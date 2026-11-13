"""Run the full UK Carbon & REGO monitor pipeline.

Public-source fetch steps are "soft": if one fails (site down, workbook layout
changed), the previous committed extract is kept, the failure is recorded in
``data/processed/build_status.json`` and surfaced on the dashboard by source
control SC-010, and the rest of the pipeline still runs. The command exits
non-zero at the end so the failure is visible, unless ``--allow-fetch-failures``
is passed (used by the scheduled workflow, which then fails in a later step,
after committing the otherwise-refreshed outputs).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from project_paths import ROOT


SRC = Path(__file__).resolve().parent
BUILD_STATUS = ROOT / "data" / "processed" / "build_status.json"

FETCH_DATASETS = {
    "SRC-009": "GOV.UK Fuel Mix Disclosure table",
    "SRC-011": "ECB EUR/GBP reference rates",
    "SRC-004": "EEX EUA auction results",
    "SRC-005": "NESO Carbon Intensity API",
    "SRC-007": "GOV.UK UK ETS CCM monthly prices",
}

# (script, source_id) — a source_id marks a soft public-source fetch step.
STEPS: list[tuple[str, str | None]] = [
    ("rego_controls.py", None),
    ("customer_claim_coverage.py", None),
    ("scope2_readiness.py", None),
    ("claim_evidence_register.py", None),
    ("fetch_fmd.py", "SRC-009"),
    ("fmd_context.py", None),
    ("validate_uka_auction_input.py", None),
    ("fetch_eex_eua_auctions.py", "SRC-004"),
    ("fetch_uk_ets_ccm.py", "SRC-007"),
    ("fetch_ecb_fx.py", "SRC-011"),
    ("carbon_signals.py", None),
    ("carbon_cost_context.py", None),
    ("fetch_tradingeconomics_reference.py", None),
    ("auction_signals.py", None),
    ("fetch_neso.py", "SRC-005"),
    ("power_signals.py", None),
    ("source_controls.py", None),
    ("build_dashboard_data.py", None),
    ("build_analyst_note.py", None),
]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_status(started_at: str, failures: list[dict[str, str]], completed: bool) -> None:
    BUILD_STATUS.parent.mkdir(parents=True, exist_ok=True)
    BUILD_STATUS.write_text(
        json.dumps(
            {"started_at": started_at, "completed": completed, "failed_steps": failures},
            indent=2,
        ),
        encoding="utf-8",
    )


def last_error_line(output: str) -> str:
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    return lines[-1][:500] if lines else "No error output captured."


def run_step(script: str, soft: bool) -> subprocess.CompletedProcess[str] | None:
    print(f"Running {script}...", flush=True)
    if not soft:
        subprocess.run([sys.executable, str(SRC / script)], check=True)
        return None
    result = subprocess.run([sys.executable, str(SRC / script)], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--allow-fetch-failures",
        action="store_true",
        help="Exit 0 even if a public-source fetch failed (failures are still recorded in build_status.json).",
    )
    args = parser.parse_args(argv)

    started_at = utc_now()
    failures: list[dict[str, str]] = []
    write_status(started_at, failures, completed=False)

    for script, source_id in STEPS:
        result = run_step(script, soft=source_id is not None)
        if result is not None and result.returncode != 0:
            error = last_error_line(result.stderr or result.stdout)
            print(f"WARNING: {script} failed; keeping the previous extract. {error}", file=sys.stderr, flush=True)
            failures.append(
                {"step": script, "source_id": str(source_id), "dataset": FETCH_DATASETS.get(str(source_id), script), "error": error}
            )
            write_status(started_at, failures, completed=False)

    write_status(started_at, failures, completed=True)
    if failures:
        print(f"Dashboard pipeline complete with {len(failures)} failed fetch step(s): "
              + ", ".join(item["step"] for item in failures))
        return 0 if args.allow_fetch_failures else 1
    print("Full dashboard pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
