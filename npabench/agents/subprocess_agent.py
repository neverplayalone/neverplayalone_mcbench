from __future__ import annotations

import os
import signal
import subprocess
import threading
from typing import Iterator

from npabench.agents.base import Agent, AgentRunContext
from npabench.agents.event_stream import pump_trace_events
from npabench.agents.launcher import detect_launch
from npabench.evaluation.run_trace import TraceEvent


class SubprocessAgent(Agent):
    def __init__(self, spec):
        super().__init__(spec)
        self.child_process: subprocess.Popen[str] | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stderr_lines: list[str] = []

    def run(self, context: AgentRunContext) -> Iterator[TraceEvent]:
        path = self.spec.path.resolve()
        command = detect_launch(path) + (self.spec.extra_args or [])
        env = {
            **os.environ,
            "NPABENCH_HOST": context.host,
            "NPABENCH_PORT": str(context.port),
            "NPABENCH_AGENT_USERNAME": context.username,
            "NPABENCH_AGENT_PROMPT": context.prompt,
            "NPABENCH_TIMEOUT_SECONDS": str(context.timeout_seconds),
        }
        cwd = path if path.is_dir() else path.parent
        self.child_process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, daemon=True
        )
        self._stderr_thread.start()

        yield from pump_trace_events(
            self.child_process,
            context.timeout_seconds,
            lambda: self.stderr_log,
        )

    def stop(self) -> None:
        if not self.child_process:
            return
        if self.child_process.poll() is None:
            try:
                self.child_process.send_signal(signal.SIGTERM)
                self.child_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.child_process.kill()
        self.child_process = None

    @property
    def stderr_log(self) -> list[str]:
        return list(self._stderr_lines)

    def _drain_stderr(self) -> None:
        assert self.child_process and self.child_process.stderr
        for line in self.child_process.stderr:
            self._stderr_lines.append(line.rstrip("\n"))
