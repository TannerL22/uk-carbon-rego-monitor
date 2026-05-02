"""Run the full UK Carbon & REGO monitor pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    "rego_controls.py",
    "fetch_eex_eua_auctions.py",
    "fetch_uk_ets_ccm.py",
    "carbon_signals.py",
    "auction_signals.py",
    "fetch_neso.py",
    "power_signals.py",
    "source_controls.py",
    "build_dashboard_data.py",
]


def main() -> None:
    for step in STEPS:
        print(f"Running {step}...")
        subprocess.run([sys.executable, str(ROOT / "src" / step)], check=True)
    print("Full dashboard pipeline complete.")


if __name__ == "__main__":
    main()
