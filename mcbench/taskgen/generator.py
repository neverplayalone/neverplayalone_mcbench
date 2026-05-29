"""Expand a style+seed into a TaskConfig and write it as a task YAML."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..config import TaskConfig
from .base import stable_rng
from .styles import STYLES

_OFFSET_RE = re.compile(r"~(-?\d+) ~(-?\d+) ~(-?\d+)")


def _assert_within_bounds(cfg: TaskConfig) -> None:
    """Invariant: every `~`-relative placement must sit inside the task's reset box.

    Anything outside the reset box would survive the between-run reset and leak
    into the next task, so generation refuses to emit such a config.
    """
    for cmd in cfg.setup.commands:
        for dx, dy, dz in _OFFSET_RE.findall(cmd):
            horiz = max(abs(int(dx)), abs(int(dz)))
            if horiz > cfg.reset_radius:
                raise ValueError(
                    f"placement {dx},{dy},{dz} exceeds reset_radius {cfg.reset_radius} in {cfg.id}"
                )
            if int(dy) > cfg.reset_ceiling:
                raise ValueError(
                    f"placement height {dy} exceeds reset_ceiling {cfg.reset_ceiling} in {cfg.id}"
                )


def generate(style_id: str, seed: int, difficulty: str = "simple") -> TaskConfig:
    if style_id not in STYLES:
        raise KeyError(f"unknown style {style_id!r}; known: {sorted(STYLES)}")
    rng = stable_rng(style_id, difficulty, seed)
    cfg = STYLES[style_id].generate(rng, difficulty)
    _assert_within_bounds(cfg)
    return cfg


def write_task(cfg: TaskConfig, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = cfg.model_dump(exclude_none=True)
    path = out / f"{cfg.id}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path
