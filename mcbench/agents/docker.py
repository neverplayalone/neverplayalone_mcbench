"""DockerAgent: run an untrusted agent inside a sandboxed container.

Same JSONL-over-stdout contract as :class:`SubprocessAgent` — the only
difference is the launch command. Instead of running ``node index.js`` directly
on the host (where malicious agent code has the operator's privileges), the
agent is run inside a container built from ``docker/agent`` with:

  * the agent directory bind-mounted **read-only** at ``/agent`` (no host writes),
  * dependencies resolved from the image's baked ``node_modules`` via NODE_PATH,
  * a dropped capability set, no new privileges, a non-root user, a read-only
    rootfs (writable ``/tmp`` only), and pid/memory caps,
  * the Minecraft server reached by container name on a dedicated per-slot
    Docker network. RCON is still published only on loopback for the harness and
    protected by a per-slot random password.

``docker run`` is itself a child process whose stdout is the agent's stdout, so
the streaming/timeout loop is shared with the subprocess path.
"""

from __future__ import annotations

import hashlib
import subprocess
import threading
from pathlib import Path
from typing import Iterator

from rich.console import Console

from mcbench.core.trace import TraceEvent
from mcbench.agents.base import Agent, AgentRunContext
from mcbench.agents._process_stream import pump_events
from mcbench.paths import DOCKER_DIR

console = Console()

AGENT_IMAGE_DIR = DOCKER_DIR / "agent"
AGENT_IMAGE_REPO = "mcbench-agent-runtime"
SERVER_CONTAINER_PORT = 25565

# Container-side sandbox defaults. The agent never needs much; these cap a
# runaway or hostile agent without affecting a well-behaved one.
DEFAULT_MEMORY = "1g"
DEFAULT_PIDS_LIMIT = 256


def agent_image_tag() -> str:
    """Image tag derived from the runtime recipe, so dep changes rebuild it."""
    recipe = (AGENT_IMAGE_DIR / "package.json").read_bytes()
    recipe += (AGENT_IMAGE_DIR / "Dockerfile").read_bytes()
    digest = hashlib.sha256(recipe).hexdigest()[:12]
    return f"{AGENT_IMAGE_REPO}:{digest}"


def ensure_agent_image(tag: str | None = None) -> str:
    """Build the agent runtime image if it is not already present. Returns the tag."""
    tag = tag or agent_image_tag()
    present = (
        subprocess.run(
            ["docker", "image", "inspect", tag],
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )
    if not present:
        console.log(f"Building agent runtime image [bold]{tag}[/] (one-time)...")
        result = subprocess.run(
            ["docker", "build", "-t", tag, str(AGENT_IMAGE_DIR)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"building agent image failed (exit {result.returncode})\n"
                f"--- stderr ---\n{result.stderr}\n--- stdout ---\n{result.stdout}"
            )
    return tag


class DockerAgent(Agent):
    def __init__(
        self,
        spec,
        *,
        container_name: str,
        network_name: str,
        server_host: str,
        server_port: int = SERVER_CONTAINER_PORT,
        image: str | None = None,
        memory: str = DEFAULT_MEMORY,
        pids_limit: int = DEFAULT_PIDS_LIMIT,
    ):
        super().__init__(spec)
        self.container_name = container_name
        self.network_name = network_name
        self.server_host = server_host
        self.server_port = server_port
        self.image = image  # resolved lazily in run() if None
        self.memory = memory
        self.pids_limit = pids_limit
        self.proc: subprocess.Popen | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stderr_lines: list[str] = []

    def docker_run_cmd(self, ctx: AgentRunContext, image: str) -> list[str]:
        """The full ``docker run`` argv for this agent. Pure, for testability."""
        agent_dir = Path(self.spec.path).resolve()
        if not agent_dir.is_dir():
            raise NotADirectoryError(
                f"docker mode needs an agent directory (with index.js), got {agent_dir}"
            )
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            self.container_name,
            # --- isolation ---
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,size=64m",
            "--pids-limit",
            str(self.pids_limit),
            "--memory",
            self.memory,
            # --- code in, read-only ---
            "-v",
            f"{agent_dir}:/agent:ro",
            "-w",
            "/agent",
            # --- reach only the slot server over the dedicated Docker network ---
            "--network",
            self.network_name,
            "-e",
            f"MCBENCH_HOST={self.server_host}",
            "-e",
            f"MCBENCH_PORT={self.server_port}",
            "-e",
            f"MCBENCH_USERNAME={ctx.username}",
            "-e",
            f"MCBENCH_GOAL={ctx.goal}",
            "-e",
            f"MCBENCH_TIMEOUT={ctx.timeout_seconds}",
            image,
            "node",
            "index.js",
        ]

    def run(self, ctx: AgentRunContext) -> Iterator[TraceEvent]:
        image = self.image or ensure_agent_image()
        self.image = image
        # A stale container from a crashed prior run would make --name collide.
        subprocess.run(
            ["docker", "rm", "-f", self.container_name],
            capture_output=True,
            text=True,
        )
        cmd = self.docker_run_cmd(ctx, image)
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

        yield from pump_events(self.proc, ctx.timeout_seconds, lambda: self.stderr_log)

    def stop(self) -> None:
        # The container is the source of truth; removing it makes the foreground
        # `docker run` client exit. Done after capture, so the bot stays connected
        # through the final-state snapshot.
        subprocess.run(
            ["docker", "rm", "-f", self.container_name],
            capture_output=True,
            text=True,
        )
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    @property
    def stderr_log(self) -> list[str]:
        return list(self._stderr_lines)

    def _drain_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            self._stderr_lines.append(line.rstrip("\n"))
