"""Filesystem locations used across the harness."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKER_DIR = REPO_ROOT / "docker"
RESULTS_DIR = REPO_ROOT / "results" / "resource_gathering"
