import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = ROOT / "data" / "processed" / "scope2_readiness.json"
SUMMARY_PATH = ROOT / "data" / "processed" / "scope2_readiness_summary.json"


class Scope2ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(ROOT / "src" / "rego_controls.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "customer_claim_coverage.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "scope2_readiness.py")], check=True)
        cls.rows = {
            row["contract_id"]: row
            for row in json.loads(READINESS_PATH.read_text(encoding="utf-8"))
        }
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_every_customer_contract_receives_readiness_status(self) -> None:
        self.assertEqual({"C-001", "C-002", "C-003"}, set(self.rows))
        for row in self.rows.values():
            self.assertIn(row["future_scope2_readiness"], {"Low", "Medium", "High"})
            self.assertTrue(row["primary_readiness_gap"])

    def test_readiness_is_separate_from_current_annual_status(self) -> None:
        self.assertEqual("Not supportable", self.rows["C-001"]["current_annual_claim_status"])
        self.assertEqual("Low", self.rows["C-001"]["future_scope2_readiness"])
        self.assertEqual("Review", self.rows["C-003"]["current_annual_claim_status"])
        self.assertEqual("Medium", self.rows["C-003"]["future_scope2_readiness"])

    def test_summary_counts_and_methodology_are_explicit(self) -> None:
        self.assertEqual(3, self.summary["contracts_assessed"])
        self.assertEqual(0, self.summary["high_readiness"])
        self.assertEqual(1, self.summary["medium_readiness"])
        self.assertEqual(2, self.summary["low_readiness"])
        self.assertIn("not a compliance calculation", self.summary["methodology_note"])
        self.assertIn("Current annual claim status", self.summary["methodology_note"])

    def test_no_24_7_matching_or_official_scope2_claim(self) -> None:
        notes = {row["methodology_note"] for row in self.rows.values()}
        self.assertEqual(1, len(notes))
        note = notes.pop()
        self.assertIn("does not apply final Scope 2 rules", note)
        self.assertIn("does not", note)
        self.assertIn("24/7 matching", note)


if __name__ == "__main__":
    unittest.main()
