from __future__ import annotations

from npabench.agents.base import AgentRunContext, AgentSpec
from npabench.agents.sandboxed_agent import SandboxedAgent
from npabench.agents.subprocess_agent import SubprocessAgent


def _context() -> AgentRunContext:
    return AgentRunContext(
        host="127.0.0.1",
        port=25565,
        username="npabench_agent",
        prompt="Collect 24 logs and return to spawn.",
        timeout_seconds=120,
    )


def test_sandboxed_agent_passes_prompt_but_not_task_json(tmp_path) -> None:
    agent = SandboxedAgent(
        AgentSpec(name="agent", path=tmp_path),
        container_name="npabench-agent-0",
        network_name="npabench-net",
        server_host="server",
    )

    command = agent.docker_run_cmd(_context(), image="image:latest")

    assert any("NPABENCH_AGENT_PROMPT=" in part for part in command)
    assert not any("NPABENCH_TASK_JSON=" in part for part in command)


def test_subprocess_agent_passes_prompt_but_not_task_json(monkeypatch, tmp_path) -> None:
    (tmp_path / "package.json").write_text("{}")
    captured = {}

    class FakePopen:
        def __init__(self, command, cwd, env, stdout, stderr, text, bufsize):
            captured["env"] = env
            self.stdout = []
            self.stderr = []

    monkeypatch.setattr("npabench.agents.subprocess_agent.subprocess.Popen", FakePopen)
    monkeypatch.setattr(
        "npabench.agents.subprocess_agent.pump_trace_events",
        lambda *args, **kwargs: iter(()),
    )
    agent = SubprocessAgent(AgentSpec(name="agent", path=tmp_path))

    list(agent.run(_context()))

    assert captured["env"]["NPABENCH_AGENT_PROMPT"] == _context().prompt
    assert "NPABENCH_TASK_JSON" not in captured["env"]
