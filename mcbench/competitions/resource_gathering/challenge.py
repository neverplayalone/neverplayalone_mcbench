"""Catalog entries, the generated challenge, and deterministic challenge generation."""

from __future__ import annotations

import random

from pydantic import BaseModel, Field, field_validator

from ...core.competition import RunConfig
from .config import ResourceCompetitionConfig, ResourceTarget


class ResourceCatalogEntry(BaseModel):
    """One logical resource that can be selected for a challenge."""

    items: list[str]
    target_range: tuple[int, int]
    points: float = 100.0
    display_name: str | None = None
    # Optional biome to pin the whole world to (e.g. "minecraft:forest"), so the
    # resource is guaranteed present near spawn instead of depending on the seed.
    # None => normal multi-biome generation.
    biome: str | None = None

    @field_validator("items")
    @classmethod
    def items_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("catalog resource must count at least one item")
        return value

    @field_validator("target_range")
    @classmethod
    def target_range_must_be_valid(cls, value: tuple[int, int]) -> tuple[int, int]:
        lo, hi = value
        if lo <= 0 or hi <= 0 or lo > hi:
            raise ValueError("target_range must be positive and increasing")
        return value


class ResourceCatalog(BaseModel):
    resources: dict[str, ResourceCatalogEntry]

    @field_validator("resources")
    @classmethod
    def resources_must_not_be_empty(
        cls, value: dict[str, ResourceCatalogEntry]
    ) -> dict[str, ResourceCatalogEntry]:
        if not value:
            raise ValueError("resource catalog cannot be empty")
        return value


class GeneratedChallenge(BaseModel):
    """The frozen task all miners in one batch receive."""

    challenge_id: str
    seed: int
    world_seed: int
    resource: str
    items: list[str]
    target_count: int
    points: float
    goal: str
    duration_seconds: int
    minecraft_version: str
    world_type: str
    generate_structures: bool
    difficulty: str
    spawn_time: int
    biome: str | None = None

    def to_run_config(self, base_cfg: ResourceCompetitionConfig) -> ResourceCompetitionConfig:
        data = base_cfg.model_dump()
        data.update(
            {
                "id": self.challenge_id,
                "seed": self.world_seed,
                "minecraft_version": self.minecraft_version,
                "world_type": self.world_type,
                "generate_structures": self.generate_structures,
                "difficulty": self.difficulty,
                "duration_seconds": self.duration_seconds,
                "spawn_time": self.spawn_time,
                "biome": self.biome,
                "goal": self.goal,
                "resources": [
                    ResourceTarget(
                        item=self.resource,
                        items=self.items,
                        target_count=self.target_count,
                        points=self.points,
                    ).model_dump()
                ],
            }
        )
        return ResourceCompetitionConfig.model_validate(data)


def generate_challenge(
    catalog: ResourceCatalog,
    base_cfg: RunConfig,
    seed: int,
    challenge_id: str | None = None,
) -> GeneratedChallenge:
    rng = random.Random(seed)
    resource = rng.choice(sorted(catalog.resources))
    entry = catalog.resources[resource]
    target_count = rng.randint(*entry.target_range)
    world_seed = rng.randint(-(2**31), 2**31 - 1)
    display_name = entry.display_name or resource.replace("_", " ")
    challenge_id = challenge_id or f"resource_{seed}_{resource}_{target_count}"
    goal = (
        f"Before sunset, gather {target_count} {display_name}. "
        "Keep the items in your inventory and finish within 20 blocks of spawn."
    )
    return GeneratedChallenge(
        challenge_id=challenge_id,
        seed=seed,
        world_seed=world_seed,
        resource=resource,
        items=entry.items,
        target_count=target_count,
        points=entry.points,
        goal=goal,
        duration_seconds=base_cfg.duration_seconds,
        minecraft_version=base_cfg.minecraft_version,
        world_type=base_cfg.world_type,
        generate_structures=base_cfg.generate_structures,
        difficulty=base_cfg.difficulty,
        spawn_time=base_cfg.spawn_time,
        biome=entry.biome,
    )
