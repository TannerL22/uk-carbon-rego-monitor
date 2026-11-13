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

    def test_remove_source_drops_only_matching_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "register.csv"
            source_register.upsert_source({"source_id": "SRC-001"}, path)
            source_register.upsert_source({"source_id": "SRC-003"}, path)
            source_register.remove_source("SRC-003", path)
            source_register.remove_source("SRC-999", path)
            self.assertEqual(["SRC-001"], [r["source_id"] for r in source_register.read_register(path)])

    def test_update_fields_ignores_missing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "register.csv"
            source_register.upsert_source({"source_id": "SRC-005", "downloaded_at": "old"}, path)
            source_register.update_source_fields("SRC-005", {"downloaded_at": "new"}, path)
            source_register.update_source_fields("SRC-999", {"downloaded_at": "x"}, path)
            rows = source_register.read_register(path)
            self.assertEqual(1, len(rows))
            self.assertEqual("new", rows[0]["downloaded_at"])


UKA_HEADER = (
    "market,auction_date,auction_volume,clearing_price,currency,cover_ratio,reference_price,"
    "source,source_url,downloaded_at,manual_update_note,notes\n"
)


class SourceControlTests(IsolatedPipelineTestCase):
    """Committed state: header-only UKA file plus a simulated fetch failure."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        status = cls.root / "data" / "processed" / "build_status.json"
        status.write_text(
            json.dumps(
                {
                    "completed": True,
                    "failed_steps": [{"step": "fetch_neso.py", "source_id": "SRC-005", "dataset": "NESO Carbon Intensity API", "error": "HTTP 503"}],
                }
            ),
            encoding="utf-8",
        )
        cls.run_script("validate_uka_auction_input.py", "carbon_signals.py", "auction_signals.py", "source_controls.py")
        cls.summary = cls.read_processed("source_quality_summary.json")
        cls.by_control = {}
        for issue in cls.summary["issues"]:
            cls.by_control.setdefault(issue["control_id"], []).append(issue)

    def test_header_only_uka_file_is_valid_and_not_registered(self) -> None:
        self.assertNotIn("SC-008", self.by_control)
        rows = {row["source_id"] for row in source_register.read_register(self.root / "data" / "source_register.csv")}
        self.assertNotIn("SRC-003", rows)
        uka = self.read_processed("auction_signals.json")["uka"]
        self.assertFalse(uka["available"])
        self.assertIn("not loaded", uka["demand_signal"])

    def test_fetch_failures_are_surfaced(self) -> None:
        [issue] = self.by_control["SC-010"]
        self.assertEqual("SRC-005", issue["source_id"])
        self.assertEqual("NESO Carbon Intensity API", issue["dataset_name"])
        self.assertIn("HTTP 503", issue["issue"])
        self.assertEqual(1, self.summary["failed_fetch_count"])

    def test_timestamped_downloads_are_parsed_for_staleness(self) -> None:
        # Mixed date-only and ISO-timestamp values must all parse; otherwise SC-004 silently never fires.
        register = (self.root / "data" / "source_register.csv").read_text(encoding="utf-8")
        self.assertIn("T", register)
        self.assertEqual(self.summary["stale_source_count"], len(self.by_control.get("SC-004", [])))


class UkaCrossCheckTests(IsolatedPipelineTestCase):
    """A UKA auction row far from the official GOV.UK monthly average must raise SC-008."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        ccm = (cls.root / "data" / "raw" / "carbon" / "uk_ets_ccm_monthly_prices.csv").read_text(encoding="utf-8")
        assert ",2026-09," in ccm, "fixture expects a CCM row covering September 2026"
        # Test fixture only: a deliberately wrong price (official September 2026 average was about GBP 60).
        (cls.root / "data" / "raw" / "carbon" / "uka_auction_results.csv").write_text(
            UKA_HEADER
            + "UKA,2026-09-16,3000000,30.0,GBP,1.5,30.0,Test fixture - not verified,https://example.test,"
            "2026-11-13,Test fixture,Deliberately wrong price for the SC-008 test\n",
            encoding="utf-8",
        )
        cls.run_script("validate_uka_auction_input.py", "carbon_signals.py", "source_controls.py")
        cls.summary = cls.read_processed("source_quality_summary.json")

    def test_deviating_uka_price_raises_sc008(self) -> None:
        [issue] = [item for item in self.summary["issues"] if item["control_id"] == "SC-008"]
        self.assertEqual("SRC-003", issue["source_id"])
        self.assertEqual("High", issue["severity"])

    def test_unverified_rows_are_labelled_illustrative_in_register(self) -> None:
        rows = {row["source_id"]: row for row in source_register.read_register(self.root / "data" / "source_register.csv")}
        self.assertIn("illustrative", rows["SRC-003"]["source_type"])


if __name__ == "__main__":
    unittest.main()
