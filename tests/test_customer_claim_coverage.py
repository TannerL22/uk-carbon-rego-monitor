import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_PATH = ROOT / "data" / "processed" / "customer_claim_coverage.json"
SUMMARY_PATH = ROOT / "data" / "processed" / "customer_claim_summary.json"


class CustomerClaimCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(ROOT / "src" / "rego_controls.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "customer_claim_coverage.py")], check=True)
        cls.coverage = {
            row["contract_id"]: row
            for row in json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
        }
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_each_customer_contract_receives_claim_status(self) -> None:
        self.assertEqual({"C-001", "C-002", "C-003"}, set(self.coverage))
        for row in self.coverage.values():
            self.assertIn(row["claim_status"], {"Covered", "Review", "Shortfall", "Not supportable"})
            self.assertTrue(row["primary_issue"])

    def test_claim_status_is_contract_scoped(self) -> None:
        self.assertEqual("Not supportable", self.coverage["C-001"]["claim_status"])
        self.assertEqual("Not supportable", self.coverage["C-002"]["claim_status"])
        self.assertEqual("Review", self.coverage["C-003"]["claim_status"])
        self.assertEqual(900, self.summary["uncovered_mwh"])
        self.assertEqual(6412.5, self.summary["estimated_cover_cost_gbp"])

    def test_context_is_not_claim_validity_input(self) -> None:
        notes = {row["methodology_note"] for row in self.coverage.values()}
        self.assertEqual(1, len(notes))
        note = notes.pop()
        self.assertIn("Grid intensity and carbon prices are context layers", note)
        self.assertIn("do not determine claim validity", note)


if __name__ == "__main__":
    unittest.main()
