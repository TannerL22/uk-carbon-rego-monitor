import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "carbon_cost_context.json"


class CarbonCostContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(ROOT / "src" / "rego_controls.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "customer_claim_coverage.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "fmd_context.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "carbon_signals.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "carbon_cost_context.py")], check=True)
        cls.context = json.loads(OUTPUT.read_text(encoding="utf-8"))

    def test_carbon_cost_context_shape(self) -> None:
        self.assertEqual("Indicative carbon-cost context", self.context["label"])
        self.assertEqual(28.0, self.context["auction_reserve_price_gbp_per_tco2"])
        self.assertEqual("2026-04-08", self.context["auction_reserve_price_effective_from"])
        self.assertEqual(3, len(self.context["rows"]))

    def test_calculations_are_context_only(self) -> None:
        rows = {row["factor_id"]: row for row in self.context["rows"]}
        residual = rows["FMD_RESIDUAL_MIX"]
        expected = round(
            self.context["latest_uka_price_gbp_per_tco2"]
            * residual["emissions_factor_gco2_per_kwh"]
            / 1000,
            2,
        )
        self.assertEqual(expected, residual["indicative_carbon_cost_gbp_per_mwh"])
        self.assertIn("not a REGO claim validation input", self.context["methodology_note"])
        self.assertIn("not a bill calculation", self.context["methodology_note"])


if __name__ == "__main__":
    unittest.main()
