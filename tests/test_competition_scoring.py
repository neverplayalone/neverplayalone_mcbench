from __future__ import annotations

import time
import unittest

from mcbench.competition import (
    CompetitionScoringConfig,
    KitItem,
    ResourceCompetitionConfig,
    ResourceTarget,
    _count_item_stacks,
    _kit_item_stack,
    score_resource_gathering,
)
from mcbench.trace import FinalState, Trace, TraceEvent


def _config() -> ResourceCompetitionConfig:
    return ResourceCompetitionConfig(
        id="test_gather",
        duration_seconds=1200,
        resources=[
            ResourceTarget(item="oak_log", target_count=64, points=100),
        ],
        scoring=CompetitionScoringConfig(
            survival_points=50,
            efficiency_points=50,
            efficiency_min_resource_score=100,
        ),
    )


class CompetitionScoringTest(unittest.TestCase):
    def test_resource_config_defaults_to_minecraft_1_21_11(self) -> None:
        cfg = _config()

        self.assertEqual(cfg.minecraft_version, "1.21.11")
        self.assertEqual(cfg.world_type, "normal")

    def test_kit_item_stack_uses_1_21_item_components(self) -> None:
        item = _kit_item_stack(
            KitItem(
                item="netherite_pickaxe",
                enchantments=["efficiency:5", "unbreaking:3", "fortune:3"],
            )
        )

        self.assertEqual(
            item,
            'minecraft:netherite_pickaxe[minecraft:enchantments={"minecraft:efficiency":5,'
            '"minecraft:unbreaking":3,"minecraft:fortune":3}]',
        )

    def test_target_count_scoring_caps_logical_resource_group(self) -> None:
        cfg = ResourceCompetitionConfig(
            id="target_logs",
            duration_seconds=1200,
            resources=[
                ResourceTarget(
                    item="logs",
                    items=["oak_log", "birch_log"],
                    target_count=10,
                    points=100,
                )
            ],
            scoring=CompetitionScoringConfig(
                survival_points=0,
                efficiency_points=0,
                efficiency_min_resource_score=100,
            ),
        )
        trace = Trace(task_id=cfg.id, agent_name="agent", started_at=time.time() - 1200)
        trace.ended_at = time.time()
        trace.timed_out = True
        trace.final_state = FinalState(inventory={"oak_log": 3, "birch_log": 2}, health=20)

        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 50)
        self.assertEqual(report["resources"][0]["count"], 5)

        trace.final_state.inventory = {"oak_log": 30}
        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 100)
        self.assertEqual(report["resources"][0]["count"], 30)

    def test_count_item_stacks_parses_spawn_storage_contents(self) -> None:
        raw = (
            'Block data: [{Slot: 0b, count: 64, id: "minecraft:oak_log"}, '
            '{Slot: 1b, count: 12, id: "minecraft:birch_log"}, '
            '{Slot: 2b, count: 3, id: "minecraft:oak_log"}]'
        )

        self.assertEqual(_count_item_stacks(raw, "oak_log"), 67)
        self.assertEqual(_count_item_stacks(raw, "birch_log"), 12)
        self.assertEqual(_count_item_stacks(raw, "coal"), 0)

    def test_scores_target_count_and_survival(self) -> None:
        cfg = _config()
        trace = Trace(task_id=cfg.id, agent_name="agent", started_at=time.time() - 1200)
        trace.ended_at = time.time()
        trace.timed_out = True
        trace.final_state = FinalState(inventory={"oak_log": 32}, health=20)

        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 50)
        self.assertEqual(report["survival_score"], 50)
        self.assertEqual(report["efficiency_score"], 0)
        self.assertEqual(report["score"], 100)

    def test_efficiency_bonus_requires_early_done_and_resource_floor(self) -> None:
        cfg = _config()
        trace = Trace(task_id=cfg.id, agent_name="agent", started_at=time.time() - 300)
        trace.ended_at = time.time()
        trace.final_state = FinalState(inventory={"oak_log": 32}, health=20)
        trace.append(TraceEvent(kind="done", data={}))

        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 50)
        self.assertEqual(report["efficiency_score"], 0)

        trace.final_state.inventory["oak_log"] = 64
        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 100)
        self.assertGreater(report["efficiency_score"], 0)


if __name__ == "__main__":
    unittest.main()
