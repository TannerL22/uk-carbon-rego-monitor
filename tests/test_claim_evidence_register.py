import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data" / "processed" / "claim_evidence_register.json"
SUMMARY_PATH = ROOT / "data" / "processed" / "claim_evidence_summary.json"


class ClaimEvidenceRegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(ROOT / "src" / "rego_controls.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "customer_claim_coverage.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "claim_evidence_register.py")], check=True)
        cls.rows = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    def test_register_covers_exception_register(self) -> None:
        self.assertGreaterEqual(len(self.rows), 10)
        self.assertEqual(len(self.rows), self.summary["register_items"])
        for row in self.rows:
            self.assertTrue(row["evidence_register_id"].startswith("ER-"))
            self.assertTrue(row["exception_id"].startswith("EX-"))
            self.assertTrue(row["remediation_action"])
            self.assertTrue(row["exception_owner"])
            self.assertTrue(row["target_resolution_date"])

    def test_customer_and_fmd_impact_are_visible(self) -> None:
        customer_impacting = [row for row in self.rows if row["customer_claim_impact"] == "Customer-impacting"]
        fmd_impacting = [row for row in self.rows if row["fmd_impact"] == "FMD-impacting"]
        self.assertGreater(len(customer_impacting), 0)
        self.assertGreater(len(fmd_impacting), 0)
        self.assertEqual(len(customer_impacting), self.summary["customer_impacting_items"])
        self.assertEqual(len(fmd_impacting), self.summary["fmd_impacting_items"])

    def test_high_severity_items_are_open_with_owner_and_action(self) -> None:
        high_rows = [row for row in self.rows if row["severity"] == "High"]
        self.assertEqual(len(high_rows), self.summary["high_severity_items"])
        for row in high_rows:
            self.assertTrue(row["status"].startswith("Open"))
            self.assertNotEqual("", row["exception_owner"])
            self.assertNotEqual("", row["remediation_action"])

    def test_methodology_does_not_claim_compliance_signoff(self) -> None:
        notes = {row["methodology_note"] for row in self.rows}
        self.assertEqual(1, len(notes))
        note = notes.pop()
        self.assertIn("operating workflow aid", note)
        self.assertIn("not legal or compliance sign-off", note)


if __name__ == "__main__":
    unittest.main()
