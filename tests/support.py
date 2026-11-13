"""Test helpers: run pipeline scripts against a disposable copy of the data tree.

The pipeline scripts write into ``data/processed`` and ``outputs``. Running them
directly from tests used to rewrite tracked files on every test run. Each test
class instead copies ``data/`` and ``outputs/`` into a temporary directory and
points the scripts at it through ``UK_CARBON_MONITOR_ROOT``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
ROOT_ENV_VAR = "UK_CARBON_MONITOR_ROOT"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class IsolatedPipelineTestCase(unittest.TestCase):
    """Base class providing an isolated project root and a script runner."""

    temp_dir: tempfile.TemporaryDirectory[str]
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="uk-carbon-monitor-test-")
        cls.root = Path(cls.temp_dir.name)
        shutil.copytree(REPO_ROOT / "data", cls.root / "data")
        shutil.copytree(REPO_ROOT / "outputs", cls.root / "outputs")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()
        super().tearDownClass()

    @classmethod
    def run_script(cls, *scripts: str, args: list[str] | None = None) -> None:
        env = {**os.environ, ROOT_ENV_VAR: str(cls.root)}
        for script in scripts:
            subprocess.run(
                [sys.executable, str(SRC / script), *(args or [])],
                check=True,
                env=env,
                cwd=cls.root,
                stdout=subprocess.DEVNULL,
            )

    @classmethod
    def read_processed(cls, filename: str) -> object:
        return json.loads((cls.root / "data" / "processed" / filename).read_text(encoding="utf-8"))
