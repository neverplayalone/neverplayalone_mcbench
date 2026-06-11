"""Generic benchmark engine — task-agnostic.

Drives any :class:`Task`: Docker slots, RCON, the agent subprocess,
recording, the run loop, and parallel batching all live here.
"""

from __future__ import annotations

from .batch import (
    EvaluationBatch,
    EvaluationSlot,
    ParallelEvaluator,
    WorldTemplateBuilder,
    create_evaluation_batch,
    parse_agent_assignment,
    run_evaluation_batch,
)
from .task import USERNAME, Task, KitItem, RunConfig
from .runner import run_task
from .slot import Slot
from .trace import FinalState, Trace, TraceEvent, parse_event_line

__all__ = [
    "Task",
    "Slot",
    "EvaluationBatch",
    "EvaluationSlot",
    "FinalState",
    "KitItem",
    "ParallelEvaluator",
    "RunConfig",
    "Trace",
    "TraceEvent",
    "USERNAME",
    "WorldTemplateBuilder",
    "create_evaluation_batch",
    "parse_agent_assignment",
    "parse_event_line",
    "run_task",
    "run_evaluation_batch",
]
