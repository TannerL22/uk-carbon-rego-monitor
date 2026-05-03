import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FMD_PATH = ROOT / "data" / "processed" / "fmd_context.json"


class FmdContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(ROOT / "src" / "rego_controls.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "customer_claim_coverage.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "src" / "fmd_context.py")], check=True)
        cls.fmd = json.loads(FMD_PATH.read_text(encoding="utf-8"))

    def test_fmd_summary_shape(self) -> None:
        self.assertEqual("2024-25", self.fmd["disclosure_period"])
        self.assertEqual(154.0, self.fmd["uk_generation_average_factor_gco2_per_kwh"])
        self.assertGreater(self.fmd["fmd_residual_factor_gco2_per_kwh"], 300)
        self.assertIn("not calculate an official customer Scope 2 inventory", self.fmd["methodology_note"])

    def test_contract_context_is_context_only(self) -> None:
        rows = self.fmd["contract_context"]
        self.assertEqual(3, len(rows))
        for row in rows:
            self.assertIn("not official customer Scope 2 emissions", row["methodology_note"])
            self.assertGreaterEqual(row["location_based_emissions_proxy_tco2e"], 0)
            self.assertGreaterEqual(row["uncovered_residual_mix_context_tco2e"], 0)


if __name__ == "__main__":
    unittest.main()
