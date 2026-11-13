"""Tests for the source register helper and data-quality source controls."""

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import IsolatedPipelineTestCase

import source_register


class SourceRegisterHelperTests(unittest.TestCase):
    def test_upsert_replaces_in_place_and_appends_new_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "register.csv"
            source_register.upsert_source({"source_id": "SRC-001", "dataset_name": "A"}, path)
            source_register.upsert_source({"source_id": "SRC-002", "dataset_name": "B"}, path)
            source_register.upsert_source({"source_id": "SRC-001", "dataset_name": "A2"}, path)
            rows = source_register.read_register(path)
            self.assertEqual([("SRC-001", "A2"), ("SRC-002", "B")], [(r["source_id"], r["dataset_name"]) for r in rows])
            self.assertNotIn(b"\r\n", path.read_bytes())

    def test_update_fields_ignores_missing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "register.csv"
            source_register.upsert_source({"source_id": "SRC-005", "downloaded_at": "old"}, path)
            source_register.update_source_fields("SRC-005", {"downloaded_at": "new"}, path)
            source_register.update_source_fields("SRC-999", {"downloaded_at": "x"}, path)
            rows = source_register.read_register(path)
            self.assertEqual(1, len(rows))
            self.assertEqual("new", rows[0]["downloaded_at"])


class SourceControlTests(IsolatedPipelineTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        status = cls.root / "data" / "processed" / "build_status.json"
        status.write_text(
            json.dumps(
                {
                    "completed": True,
                    "failed_steps": [{"step": "fetch_neso.py", "source_id": "SRC-005", "error": "HTTP 503"}],
                }
            ),
            encoding="utf-8",
        )
        cls.run_script("validate_uka_auction_input.py", "carbon_signals.py", "source_controls.py")
        cls.summary = cls.read_processed("source_quality_summary.json")
        cls.by_control = {}
        for issue in cls.summary["issues"]:
            cls.by_control.setdefault(issue["control_id"], []).append(issue)

    def test_uka_input_is_cross_checked_against_official_monthly_average(self) -> None:
        # The committed UKA CSV is an illustrative sample that diverges from GOV.UK averages.
        [issue] = self.by_control["SC-008"]
        self.assertEqual("SRC-003", issue["source_id"])
        self.assertEqual("High", issue["severity"])

    def test_fetch_failures_are_surfaced(self) -> None:
        [issue] = self.by_control["SC-010"]
        self.assertEqual("SRC-005", issue["source_id"])
        self.assertIn("HTTP 503", issue["issue"])
        self.assertEqual(1, self.summary["failed_fetch_count"])

    def test_timestamped_downloads_are_parsed_for_staleness(self) -> None:
        # Mixed date-only and ISO-timestamp values must all parse; otherwise SC-004 silently never fires.
        register = (self.root / "data" / "source_register.csv").read_text(encoding="utf-8")
        self.assertIn("T", register)
        self.assertEqual(self.summary["stale_source_count"], len(self.by_control.get("SC-004", [])))

    def test_illustrative_uka_input_is_labelled_in_register(self) -> None:
        rows = {row["source_id"]: row for row in source_register.read_register(self.root / "data" / "source_register.csv")}
        self.assertIn("illustrative", rows["SRC-003"]["source_type"])


if __name__ == "__main__":
    unittest.main()
