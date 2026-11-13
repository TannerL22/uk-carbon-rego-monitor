import json
import os
import unittest

from tests.support import IsolatedPipelineTestCase, REPO_ROOT


@unittest.skipUnless(
    os.environ.get("RUN_NETWORK_TESTS") == "1",
    "Network smoke test: set RUN_NETWORK_TESTS=1 to fetch EEX, GOV.UK and NESO data.",
)
class PipelineSmokeTests(IsolatedPipelineTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # Strict mode: any failed public-source fetch fails the smoke test.
        cls.run_script("build_all.py")

    def read_json(self, relative_path: str):
        path = self.root / relative_path
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
            "data/processed/claim_evidence_register.json",
            "data/processed/claim_evidence_summary.json",
            "data/processed/fmd_context.json",
            "data/processed/carbon_cost_context.json",
            "data/processed/scope2_readiness.json",
            "data/processed/scope2_readiness_summary.json",
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
            "claim_evidence_register",
            "claim_evidence_summary",
            "scope2_readiness",
            "scope2_readiness_summary",
            "fmd_context",
            "carbon_cost_context",
            "rego_contract_summary",
            "rego_exceptions",
            "source_quality",
        }
        self.assertTrue(required_keys.issubset(summary), sorted(required_keys - set(summary)))
        self.assertEqual(6, len(summary["cards"]))
        self.assertGreaterEqual(len(summary["analyst_attention"]), 3)
        self.assertEqual(3, len(summary["rego_contract_summary"]))
        self.assertEqual(3, len(summary["customer_claim_coverage"]))
        self.assertEqual(3, len(summary["scope2_readiness"]))
        self.assertGreaterEqual(len(summary["claim_evidence_register"]), 10)
        self.assertGreaterEqual(len(summary["rego_exceptions"]), 10)

    def test_carbon_market_labels_are_supported_by_data(self) -> None:
        carbon = self.read_json("data/processed/carbon_signals.json")
        self.assertIn("latest_uka_price_gbp", carbon)
        self.assertIn("latest_eua_price_eur", carbon)
        self.assertIn("latest_eua_price_gbp", carbon)
        self.assertIn("latest_spread_gbp", carbon)
        self.assertIn("sample_period_start", carbon)
        self.assertIn("sample_period_end", carbon)
        self.assertEqual("monthly", carbon["price_basis"])
        self.assertTrue(carbon["series"], "Carbon spread series should not be empty.")
        self.assertEqual("EURGBP", carbon["fx_assumption"]["currency_pair"])
        self.assertIn("not a live traded spread", carbon["currency_note"])

    def test_build_status_reports_no_failed_fetches(self) -> None:
        status = self.read_json("data/processed/build_status.json")
        self.assertTrue(status["completed"])
        self.assertEqual([], status["failed_steps"])

    def test_rego_outputs_keep_expected_operating_shape(self) -> None:
        exceptions = self.read_json("data/processed/rego_exceptions.json")
        contracts = self.read_json("data/processed/rego_contract_summary.json")
        controls = {item["control_id"] for item in exceptions}
        self.assertIn("RC-015", controls)
        self.assertTrue(any(float(row["shortfall_mwh"]) > 0 for row in contracts))
        self.assertTrue(any(float(row["estimated_replacement_exposure_gbp"]) > 0 for row in contracts))

    def test_static_project_outputs_are_present(self) -> None:
        index = REPO_ROOT / "index.html"
        analyst_note = self.root / "outputs" / "analyst_note.md"
        self.assertTrue(index.exists(), "Missing dashboard entrypoint.")
        self.assertTrue(analyst_note.exists(), "Missing analyst note output.")
        self.assertIn("UK Carbon", index.read_text(encoding="utf-8"))
        self.assertGreater(len(analyst_note.read_text(encoding="utf-8").strip()), 500)


if __name__ == "__main__":
    unittest.main()
