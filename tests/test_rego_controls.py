import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS_PATH = ROOT / "data" / "processed" / "rego_exceptions.json"
SUMMARY_PATH = ROOT / "data" / "processed" / "rego_contract_summary.json"


class RegoControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(ROOT / "src" / "generate_synthetic_data.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "rego_controls.py")], check=True)
        cls.exceptions = json.loads(EXCEPTIONS_PATH.read_text(encoding="utf-8"))
        cls.summary = {
            row["contract_id"]: row
            for row in json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        }

    def test_expected_exception_register_shape(self) -> None:
        self.assertEqual(13, len(self.exceptions))
        self.assertEqual(8, sum(1 for item in self.exceptions if item["severity"] == "High"))
        self.assertEqual(4, sum(1 for item in self.exceptions if item["severity"] == "Medium"))
        self.assertEqual(1, sum(1 for item in self.exceptions if item["severity"] == "Low"))

    def test_each_expected_control_is_triggered(self) -> None:
        expected_controls = {
            "RC-001",
            "RC-002",
            "RC-004",
            "RC-005",
            "RC-006",
            "RC-007",
            "RC-008",
            "RC-009",
            "RC-010",
            "RC-011",
            "RC-015",
        }
        observed_controls = {item["control_id"] for item in self.exceptions}
        self.assertEqual(expected_controls, observed_controls)

    def test_intentional_bad_records_map_to_expected_controls(self) -> None:
        expected = {
            "": {"RC-001"},
            "REG-DUP-0001": {"RC-002"},
            "REG-BAD-0001": {"RC-004"},
            "REG-BAD-0002": {"RC-005"},
            "REG-BAD-0003": {"RC-006"},
            "REG-BAD-0004": {"RC-007"},
            "REG-BAD-0005": {"RC-009"},
            "REG-BAD-0006": {"RC-008"},
            "REG-BAD-0007": {"RC-010"},
            "REG-BAD-0008": {"RC-011"},
        }
        for certificate_id, controls in expected.items():
            observed = {
                item["control_id"]
                for item in self.exceptions
                if item["certificate_id"] == certificate_id
            }
            self.assertTrue(
                controls.issubset(observed),
                f"{certificate_id or '<blank>'} expected {controls}, observed {observed}",
            )

    def test_contract_shortfall_exceptions(self) -> None:
        shortfall_exceptions = {
            item["contract_id"]: item
            for item in self.exceptions
            if item["control_id"] == "RC-015"
        }
        self.assertEqual({"C-001", "C-002"}, set(shortfall_exceptions))
        self.assertIn("150 MWh", shortfall_exceptions["C-001"]["exception_message"])
        self.assertIn("750 MWh", shortfall_exceptions["C-002"]["exception_message"])

    def test_contract_coverage_and_exposure(self) -> None:
        self.assertEqual({"C-001", "C-002", "C-003"}, set(self.summary))

        self.assertContract(
            "C-001",
            required=12000,
            eligible=11850,
            ineligible=350,
            shortfall=150,
            surplus=0,
            exposure=975,
            status="Shortfall",
        )
        self.assertContract(
            "C-002",
            required=8000,
            eligible=7250,
            ineligible=300,
            shortfall=750,
            surplus=0,
            exposure=5437.5,
            status="Shortfall",
        )
        self.assertContract(
            "C-003",
            required=20000,
            eligible=20900,
            ineligible=0,
            shortfall=0,
            surplus=900,
            exposure=0,
            status="Surplus",
        )

    def assertContract(
        self,
        contract_id: str,
        required: float,
        eligible: float,
        ineligible: float,
        shortfall: float,
        surplus: float,
        exposure: float,
        status: str,
    ) -> None:
        row = self.summary[contract_id]
        self.assertEqual(required, row["required_mwh"])
        self.assertEqual(eligible, row["eligible_matched_mwh"])
        self.assertEqual(ineligible, row["ineligible_allocated_mwh"])
        self.assertEqual(shortfall, row["shortfall_mwh"])
        self.assertEqual(surplus, row["surplus_mwh"])
        self.assertEqual(exposure, row["estimated_replacement_exposure_gbp"])
        self.assertEqual(status, row["coverage_status"])


if __name__ == "__main__":
    unittest.main()
