from __future__ import annotations

import random
from typing import Literal

from mcbench.missions.base import Task, TaskTarget
from mcbench.missions.resource_gathering.config_schema import (
    MenuEntry,
    ResourceGatheringMissionConfig,
)

ESSENTIAL_TARGET_KEYS = ("logs", "cobblestone", "raw_meat")
OPTIONAL_TARGET_COUNT = 2
ESSENTIAL_POINTS = 25.0
OPTIONAL_POINTS = 12.5


def generate_task(
    base_config: ResourceGatheringMissionConfig,
    seed: int,
    task_id: str | None = None,
) -> Task:
    rng = random.Random(seed)
    targets = resolve_task_targets(base_config, rng)
    minecraft_seed = rng.getrandbits(64)
    selected_task_id = task_id or build_task_id(seed, targets)
    return Task(
        task_id=selected_task_id,
        seed=seed,
        minecraft_seed=minecraft_seed,
        targets=targets,
    )


def resolve_task_targets(
    base_config: ResourceGatheringMissionConfig,
    rng: random.Random,
) -> list[TaskTarget]:
    menu = base_config.menu
    if menu is None:
        raise ValueError("resource-gathering config has no `menu` section")

    missing_essentials = [key for key in ESSENTIAL_TARGET_KEYS if key not in menu.resources]
    if missing_essentials:
        names = ", ".join(missing_essentials)
        raise ValueError(f"resource-gathering config is missing essential targets: {names}")

    optional_keys = sorted(set(menu.resources) - set(ESSENTIAL_TARGET_KEYS))
    if len(optional_keys) < OPTIONAL_TARGET_COUNT:
        raise ValueError("resource-gathering config needs at least two optional targets")

    selected_optional_keys = rng.sample(optional_keys, OPTIONAL_TARGET_COUNT)
    selected_keys = [*ESSENTIAL_TARGET_KEYS, *selected_optional_keys]
    return [
        _build_task_target(
            key,
            menu.resources[key],
            rng,
            role="essential" if key in ESSENTIAL_TARGET_KEYS else "optional",
        )
        for key in selected_keys
    ]


def build_task_id(seed: int, targets: list[TaskTarget]) -> str:
    optional_keys = [target.key for target in targets if target.role == "optional"]
    suffix = "_".join(optional_keys) if optional_keys else "no_optionals"
    return f"resource_{seed}_{suffix}"


def _build_task_target(
    key: str,
    menu_entry: MenuEntry,
    rng: random.Random,
    *,
    role: Literal["essential", "optional"],
) -> TaskTarget:
    target_count = rng.randint(*menu_entry.target_range)
    return TaskTarget(
        key=key,
        display_name=menu_entry.display_name or key.replace("_", " "),
        items=list(menu_entry.items),
        target_count=target_count,
        role=role,
        points=ESSENTIAL_POINTS if role == "essential" else OPTIONAL_POINTS,
    )
