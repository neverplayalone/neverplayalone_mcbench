"""Shared building blocks for task styles: seeded RNG, layouts, reset bounds, commands."""

from __future__ import annotations

import hashlib
import random

# All setup commands target the benchmark bot by name; the runner ops/de-ops it.
BOT = "BenchmarkBot"

Offset = tuple[int, int, int]  # (dx, dy, dz) relative to the bot


def stable_rng(style_id: str, difficulty: str, seed: int) -> random.Random:
    """Deterministic RNG keyed by (style, difficulty, seed) — stable across machines."""
    digest = hashlib.sha256(f"{style_id}|{difficulty}|{seed}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def scatter(rng: random.Random, count: int, rmin: int = 2, rmax: int = 7) -> list[Offset]:
    """`count` distinct horizontal offsets near the bot, kept clear of its own square."""
    pts: set[tuple[int, int]] = set()
    guard = 0
    while len(pts) < count and guard < count * 50:
        guard += 1
        dx = rng.randint(-rmax, rmax)
        dz = rng.randint(-rmax, rmax)
        if abs(dx) < rmin and abs(dz) < rmin:
            continue
        pts.add((dx, dz))
    return [(dx, 0, dz) for dx, dz in sorted(pts)]


def reset_bounds(
    offsets: list[Offset],
    margin: int = 14,
    min_radius: int = 16,
    ceiling: int = 24,
) -> tuple[int, int]:
    """Reset box that fully contains the placed offsets plus a margin for agent overspill."""
    reach = max((max(abs(dx), abs(dz)) for dx, _, dz in offsets), default=0)
    return max(min_radius, reach + margin), ceiling


def at_bot(command: str) -> str:
    """Anchor a `~`-relative command to the bot's position via /execute."""
    return f"/execute at {BOT} run {command}"


def give(item: str, count: int = 1) -> str:
    return f"/give {BOT} minecraft:{item} {count}"


def pretty(name: str) -> str:
    return name.replace("_", " ")
