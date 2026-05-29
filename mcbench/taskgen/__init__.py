"""Deterministic, seeded task generation.

A *style* is a parameterized template (e.g. "mine some ore"). Given a seed it
deterministically samples its parameters — target block/mob/item, count, and
positions — and expands into a concrete `TaskConfig`. Same seed → same task, so
generated tasks are reproducible; varying the seed varies the environment, which
is what tests generalization rather than memorization of one fixed layout.
"""

from .generator import generate, write_task
from .styles import STYLES

__all__ = ["generate", "write_task", "STYLES"]
