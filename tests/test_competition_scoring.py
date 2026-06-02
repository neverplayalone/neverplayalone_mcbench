from __future__ import annotations

import time
import unittest

from mcbench.competition import (
    CompetitionScoringConfig,
    ResourceCompetitionConfig,
    ResourceMilestones,
    score_resource_gathering,
)
from mcbench.trace import FinalState, Trace, TraceEvent


def _config() -> ResourceCompetitionConfig:
    return ResourceCompetitionConfig(
        id="test_gather",
        duration_seconds=1200,
        resources=[
            ResourceMilestones(item="oak_log", milestones=[16, 64, 128, 256], points=40),
            ResourceMilestones(item="diamond", milestones=[1, 3, 8, 16], points=120),
        ],
        scoring=CompetitionScoringConfig(
            survival_points=50,
            efficiency_points=50,
            efficiency_min_resource_score=100,
        ),
    )


class CompetitionScoringTest(unittest.TestCase):
    def test_scores_resource_milestones_and_survival(self) -> None:
        cfg = _config()
        trace = Trace(task_id=cfg.id, agent_name="agent", started_at=time.time() - 1200)
        trace.ended_at = time.time()
        trace.timed_out = True
        trace.final_state = FinalState(inventory={"oak_log": 64, "diamond": 1}, health=20)

        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 50)
        self.assertEqual(report["survival_score"], 50)
        self.assertEqual(report["efficiency_score"], 0)
        self.assertEqual(report["score"], 100)

    def test_efficiency_bonus_requires_early_done_and_resource_floor(self) -> None:
        cfg = _config()
        trace = Trace(task_id=cfg.id, agent_name="agent", started_at=time.time() - 300)
        trace.ended_at = time.time()
        trace.final_state = FinalState(inventory={"diamond": 3}, health=20)
        trace.append(TraceEvent(kind="done", data={}))

        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 60)
        self.assertEqual(report["efficiency_score"], 0)

        trace.final_state.inventory["diamond"] = 8
        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 90)
        self.assertEqual(report["efficiency_score"], 0)

        trace.final_state.inventory["diamond"] = 16
        report = score_resource_gathering(cfg, trace, {"alive": True, "deaths": 0})

        self.assertEqual(report["resource_score"], 120)
        self.assertGreater(report["efficiency_score"], 0)


if __name__ == "__main__":
    unittest.main()
