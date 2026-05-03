import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


class PipelineSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / "src" / "build_all.py")],
            cwd=ROOT,
            check=True,
            timeout=240,
        )

    def read_json(self, relative_path: str):
        path = ROOT / relative_path
        self.assertTrue(path.exists(), f"Missing expected output: {relative_path}")
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_processed_outputs_exist_and_parse(self) -> None:
        expected_outputs = [
            "data/processed/dashboard_summary.json",
            "data/processed/rego_exceptions.json",
            "data/processed/rego_contract_summary.json",
            "data/processed/power_signals.json",
            "data/processed/carbon_signals.json",
            "data/processed/auction_signals.json",
            "data/processed/source_quality_summary.json",
            "data/processed/carbon_market_reference.json",
            "data/processed/customer_claim_coverage.json",
            "data/processed/customer_claim_summary.json",
            "data/processed/fmd_context.json",
        ]
        for relative_path in expected_outputs:
            self.read_json(relative_path)

    def test_dashboard_summary_contract(self) -> None:
        summary = self.read_json("data/processed/dashboard_summary.json")
        required_keys = {
            "generated_at",
            "data_basis",
            "cards",
            "analyst_attention",
            "carbon",
            "auction",
            "power",
            "customer_claim_coverage",
            "customer_claim_summary",
            "fmd_context",
            "rego_contract_summary",
            "rego_exceptions",
            "source_quality",
        }
        self.assertTrue(required_keys.issubset(summary), sorted(required_keys - set(summary)))
        self.assertEqual(6, len(summary["cards"]))
        self.assertGreaterEqual(len(summary["analyst_attention"]), 3)
        self.assertEqual(3, len(summary["rego_contract_summary"]))
        self.assertEqual(3, len(summary["customer_claim_coverage"]))
        self.assertGreaterEqual(len(summary["rego_exceptions"]), 10)

    def test_carbon_market_labels_are_supported_by_data(self) -> None:
        carbon = self.read_json("data/processed/carbon_signals.json")
        self.assertIn("latest_uka_price_gbp", carbon)
        self.assertIn("latest_eua_price_eur", carbon)
        self.assertIn("latest_eua_price_gbp", carbon)
        self.assertIn("latest_spread_gbp", carbon)
        self.assertIn("sample_period_start", carbon)
        self.assertIn("sample_period_end", carbon)
        self.assertEqual("EURGBP", carbon["fx_assumption"]["currency_pair"])
        self.assertIn("not a live traded spread", carbon["currency_note"])

    def test_rego_outputs_keep_expected_operating_shape(self) -> None:
        exceptions = self.read_json("data/processed/rego_exceptions.json")
        contracts = self.read_json("data/processed/rego_contract_summary.json")
        controls = {item["control_id"] for item in exceptions}
        self.assertIn("RC-015", controls)
        self.assertTrue(any(float(row["shortfall_mwh"]) > 0 for row in contracts))
        self.assertTrue(any(float(row["estimated_replacement_exposure_gbp"]) > 0 for row in contracts))

    def test_static_project_outputs_are_present(self) -> None:
        index = ROOT / "index.html"
        analyst_note = ROOT / "outputs" / "analyst_note.md"
        self.assertTrue(index.exists(), "Missing dashboard entrypoint.")
        self.assertTrue(analyst_note.exists(), "Missing analyst note output.")
        self.assertIn("UK Carbon", index.read_text(encoding="utf-8"))
        self.assertGreater(len(analyst_note.read_text(encoding="utf-8").strip()), 500)


if __name__ == "__main__":
    unittest.main()
