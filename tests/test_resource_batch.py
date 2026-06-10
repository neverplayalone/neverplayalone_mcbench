from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mcbench.agents import AgentSpec
from mcbench.competition import ResourceCompetitionConfig, ResourceTarget
from mcbench.resource_batch import (
    ResourceCatalog,
    ResourceCatalogEntry,
    _cleanup_slot_worlds,
    create_evaluation_batch,
    generate_challenge,
)


class ResourceBatchTest(unittest.TestCase):
    def test_generate_challenge_is_deterministic(self) -> None:
        catalog = ResourceCatalog(
            resources={
                "logs": ResourceCatalogEntry(
                    items=["oak_log", "birch_log"], target_range=(16, 128)
                ),
                "coal": ResourceCatalogEntry(items=["coal"], target_range=(8, 64)),
            }
        )
        base = ResourceCompetitionConfig(
            duration_seconds=1200,
            resources=[ResourceTarget(item="coal", target_count=8, points=100)],
        )

        first = generate_challenge(catalog, base, seed=123)
        second = generate_challenge(catalog, base, seed=123)

        self.assertEqual(first, second)
        self.assertIn(first.resource, catalog.resources)
        self.assertIn(str(first.target_count), first.goal)
        self.assertIn("within 20 blocks of spawn", first.goal)

    def test_challenge_converts_to_single_target_competition_config(self) -> None:
        catalog = ResourceCatalog(
            resources={
                "logs": ResourceCatalogEntry(
                    items=["oak_log", "birch_log"],
                    target_range=(16, 16),
                    points=100,
                )
            }
        )
        base = ResourceCompetitionConfig(
            id="base",
            duration_seconds=1200,
            resources=[ResourceTarget(item="coal", target_count=8, points=100)],
        )
        challenge = generate_challenge(catalog, base, seed=1)

        cfg = challenge.to_competition_config(base)

        self.assertEqual(cfg.id, challenge.challenge_id)
        self.assertEqual(cfg.seed, challenge.world_seed)
        self.assertEqual(cfg.goal, challenge.goal)
        self.assertEqual(len(cfg.resources), 1)
        self.assertEqual(cfg.resources[0].item, "logs")
        self.assertEqual(cfg.resources[0].items, ["oak_log", "birch_log"])
        self.assertEqual(cfg.resources[0].target_count, 16)


class CleanupSlotWorldsTest(unittest.TestCase):
    def _batch(self, output_dir: Path):
        catalog = ResourceCatalog(
            resources={"logs": ResourceCatalogEntry(items=["oak_log"], target_range=(8, 8))}
        )
        return create_evaluation_batch(
            catalog=catalog,
            base_cfg=ResourceCompetitionConfig(),
            agents=[AgentSpec(name="m", path="/tmp")],
            seed=1,
            output_dir=output_dir,
        )

    def test_removes_slot_copies_but_keeps_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "batch"
            batch = self._batch(out)

            # Disposable world copies...
            (out / "slots" / "slot-0" / "data").mkdir(parents=True)
            (out / "slots" / "slot-0" / "data" / "level.dat").write_text("x")
            (out / "template_slot" / "slot-999" / "data").mkdir(parents=True)
            # ...and the artifacts that must survive.
            (out / "world_template").mkdir(parents=True)
            (out / "world_template" / "level.dat").write_text("x")
            (out / "miners" / "m__slot0").mkdir(parents=True)
            (out / "miners" / "m__slot0" / "score.json").write_text("{}")

            _cleanup_slot_worlds(batch)

            self.assertFalse((out / "slots").exists())
            self.assertFalse((out / "template_slot").exists())
            self.assertTrue((out / "world_template" / "level.dat").exists())
            self.assertTrue((out / "miners" / "m__slot0" / "score.json").exists())

    def test_idempotent_when_nothing_to_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "batch"
            batch = self._batch(out)
            out.mkdir(parents=True)
            _cleanup_slot_worlds(batch)  # should not raise


if __name__ == "__main__":
    unittest.main()
