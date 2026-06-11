"""ResourceGatheringTask: wires the resource-gathering plugin to the engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from mcrcon import MCRcon

from mcbench.core.task import Task, RunConfig
from mcbench.core.trace import Trace
from mcbench.tasks.resource_gathering.instance import TaskInstance, generate_instance
from mcbench.tasks.resource_gathering.config import ResourceGatheringTaskConfig
from mcbench.tasks.resource_gathering.scoring import score_resource_gathering
from mcbench.tasks.resource_gathering.world import capture, configure_world, setup_agent

_CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class ResourceGatheringTask(Task):
    id = "resource_gathering_v1"

    def default_config_path(self) -> Path:
        return _CONFIG_DIR / "config.yaml"

    def load_config(self, path: str | Path) -> ResourceGatheringTaskConfig:
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return ResourceGatheringTaskConfig.model_validate(raw)

    def generate_instance(
        self,
        base_cfg: RunConfig,
        seed: int,
        instance_id: str | None = None,
    ) -> TaskInstance:
        return generate_instance(base_cfg, seed, instance_id=instance_id)

    def configure_world(self, mcr: MCRcon, cfg: RunConfig) -> None:
        configure_world(mcr, cfg)

    def setup_agent(self, mcr: MCRcon, cfg: RunConfig) -> Any:
        return setup_agent(mcr, cfg)

    def goal_text(self, cfg: RunConfig) -> str:
        return cfg.goal

    def capture(self, mcr: MCRcon, cfg: RunConfig, setup_state: Any) -> dict[str, Any]:
        return capture(mcr, cfg, setup_state)

    def score(self, cfg: RunConfig, trace: Trace, snapshot: dict[str, Any]) -> dict[str, Any]:
        return score_resource_gathering(cfg, trace, snapshot)
