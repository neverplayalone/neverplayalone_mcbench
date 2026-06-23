from __future__ import annotations

from mcbench.agents.base import AgentRunContext, AgentSpec
from mcbench.agents.sandboxed_agent import SandboxedAgent
from mcbench.agents.subprocess_agent import SubprocessAgent


def _context() -> AgentRunContext:
    return AgentRunContext(
        host="127.0.0.1",
        port=25565,
        username="mcbench_agent",
        prompt="Collect 24 logs and return to spawn.",
        timeout_seconds=120,
    )


def test_sandboxed_agent_passes_prompt_but_not_task_json(tmp_path) -> None:
    agent = SandboxedAgent(
        AgentSpec(name="agent", path=tmp_path),
        container_name="mcbench-agent-0",
        network_name="mcbench-net",
        server_host="server",
    )

    command = agent.docker_run_cmd(_context(), image="image:latest")

    assert any("MCBENCH_AGENT_PROMPT=" in part for part in command)
    assert not any("MCBENCH_TASK_JSON=" in part for part in command)


def test_subprocess_agent_passes_prompt_but_not_task_json(monkeypatch, tmp_path) -> None:
    (tmp_path / "package.json").write_text("{}")
    captured = {}

    class FakePopen:
        def __init__(self, command, cwd, env, stdout, stderr, text, bufsize):
            captured["env"] = env
            self.stdout = []
            self.stderr = []

    monkeypatch.setattr("mcbench.agents.subprocess_agent.subprocess.Popen", FakePopen)
    monkeypatch.setattr(
        "mcbench.agents.subprocess_agent.pump_trace_events",
        lambda *args, **kwargs: iter(()),
    )
    agent = SubprocessAgent(AgentSpec(name="agent", path=tmp_path))

    list(agent.run(_context()))

    assert captured["env"]["MCBENCH_AGENT_PROMPT"] == _context().prompt
    assert "MCBENCH_TASK_JSON" not in captured["env"]
