"""Shared project root resolution.

Every pipeline module reads and writes paths relative to ``ROOT``. By default
that is the repository root. Setting ``UK_CARBON_MONITOR_ROOT`` points the
pipeline at a copy of the data tree instead, which lets the test suite run the
real scripts without overwriting tracked files in ``data/`` and ``outputs/``.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT_ENV_VAR = "UK_CARBON_MONITOR_ROOT"
REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ[ROOT_ENV_VAR]).resolve() if os.environ.get(ROOT_ENV_VAR) else REPO_ROOT
