from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mcbench.agents import DockerAgent, SubprocessAgent
from mcbench.agents.base import AgentRunContext, AgentSpec
from mcbench.agents.docker import agent_image_tag
from mcbench.core.batch import make_agent
from mcbench.core.slot import Slot


def _ctx() -> AgentRunContext:
    return AgentRunContext(
        host="127.0.0.1",
        port=25665,
        username="BenchmarkBot",
        goal="gather 64 logs",
        timeout_seconds=120,
    )


class AgentImageTagTest(unittest.TestCase):
    def test_tag_is_stable_and_namespaced(self) -> None:
        tag = agent_image_tag()
        self.assertTrue(tag.startswith("mcbench-agent-runtime:"))
        self.assertEqual(tag, agent_image_tag())  # deterministic


class DockerRunCommandTest(unittest.TestCase):
    def test_command_has_sandbox_flags_and_mount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp)
            agent = DockerAgent(
                AgentSpec(name="m", path=str(agent_dir)),
                container_name="mcbench-agent-0",
            )
            cmd = agent.docker_run_cmd(_ctx(), image="mcbench-agent-runtime:test")
            joined = " ".join(cmd)

            self.assertEqual(cmd[:3], ["docker", "run", "--rm"])
            self.assertIn("--name mcbench-agent-0", joined)
            # Isolation
            self.assertIn("--cap-drop ALL", joined)
            self.assertIn("no-new-privileges", joined)
            self.assertIn("--read-only", joined)
            self.assertIn("--pids-limit", joined)
            self.assertIn("--memory", joined)
            # Code mounted read-only
            self.assertIn(f"{agent_dir}:/agent:ro", joined)
            # Reaches the server's published port via the host gateway
            self.assertIn("host.docker.internal:host-gateway", joined)
            self.assertIn("MCBENCH_HOST=host.docker.internal", joined)
            self.assertIn("MCBENCH_PORT=25665", joined)
            # Image then entrypoint last
            self.assertEqual(cmd[-3:], ["mcbench-agent-runtime:test", "node", "index.js"])

    def test_requires_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "index.js"
            f.write_text("// not a dir")
            agent = DockerAgent(
                AgentSpec(name="m", path=str(f)), container_name="mcbench-agent-0"
            )
            with self.assertRaises(NotADirectoryError):
                agent.docker_run_cmd(_ctx(), image="x")


class MakeAgentTest(unittest.TestCase):
    def test_subprocess_mode(self) -> None:
        agent = make_agent(
            AgentSpec(name="m", path="/tmp"), mode="subprocess", slot=Slot(slot_id=2)
        )
        self.assertIsInstance(agent, SubprocessAgent)

    def test_docker_mode_names_container_per_slot(self) -> None:
        agent = make_agent(
            AgentSpec(name="m", path="/tmp"),
            mode="docker",
            slot=Slot(slot_id=3),
            image="mcbench-agent-runtime:test",
        )
        self.assertIsInstance(agent, DockerAgent)
        self.assertEqual(agent.container_name, "mcbench-agent-3")
        self.assertEqual(agent.image, "mcbench-agent-runtime:test")

    def test_unknown_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            make_agent(AgentSpec(name="m", path="/tmp"), mode="vm", slot=Slot())


if __name__ == "__main__":
    unittest.main()
