"""Run config + scoring models specific to resource gathering."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ...core.competition import KitItem, RunConfig


class ResourceTarget(BaseModel):
    item: str
    items: list[str] = Field(default_factory=list)
    target_count: int
    points: float = 100.0

    @field_validator("target_count")
    @classmethod
    def target_count_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("resource target_count must be positive")
        return value


class CompetitionScoringConfig(BaseModel):
    # Final score = resource_score * distance_multiplier. distance_bands maps an
    # upper distance bound (blocks from spawn) to the multiplier applied at or
    # below it, evaluated low-to-high; beyond the last band the multiplier is
    # distance_floor_mult. Time-to-finish is not scored; it only breaks ties
    # between equal scores (see `time_efficiency` in the report).
    distance_bands: list[tuple[float, float]] = Field(
        default_factory=lambda: [
            (10.0, 1.00),
            (30.0, 0.90),
            (100.0, 0.75),
            (250.0, 0.60),
            (500.0, 0.50),
            (1000.0, 0.40),
            (2000.0, 0.30),
        ]
    )
    distance_floor_mult: float = 0.20

    @field_validator("distance_bands")
    @classmethod
    def bands_sorted_ascending(
        cls, value: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        return sorted(value, key=lambda band: band[0])


class ResourceCompetitionConfig(RunConfig):
    """Adds the resource-gathering kit, targets, and scoring to the shared RunConfig."""

    id: str = "resource_gathering_v1"
    goal: str = "Gather the requested resource before sunset."
    kit: list[KitItem] = Field(default_factory=list)
    resources: list[ResourceTarget] = Field(default_factory=list)
    scoring: CompetitionScoringConfig = Field(default_factory=CompetitionScoringConfig)
