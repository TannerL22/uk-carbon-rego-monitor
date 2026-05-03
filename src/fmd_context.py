"""Build FMD and emissions-reporting context for customer claims."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "fmd"
PROCESSED = ROOT / "data" / "processed"

FMD_INPUT = RAW / "fmd_2024_2025.csv"
CLAIM_COVERAGE = PROCESSED / "customer_claim_coverage.json"
OUTPUT_JSON = PROCESSED / "fmd_context.json"
OUTPUT_CSV = PROCESSED / "fmd_context.csv"


def read_claims() -> list[dict[str, object]]:
    with CLAIM_COVERAGE.open(encoding="utf-8") as handle:
        return json.load(handle)


def weighted_factor(rows: pd.DataFrame, mix_column: str) -> float:
    return float((rows[mix_column] * rows["emissions_factor_gco2_per_kwh"]).sum() / 100)


def tco2e_from_mwh(mwh: object, factor_gco2_per_kwh: float) -> float:
    return float(mwh) * factor_gco2_per_kwh / 1000


def build_context() -> tuple[dict[str, object], list[dict[str, object]]]:
    if not FMD_INPUT.exists():
        raise FileNotFoundError(f"Missing FMD input file: {FMD_INPUT}")

    fmd = pd.read_csv(FMD_INPUT)
    for field in [
        "uk_average_mix_pct",
        "residual_mix_pct",
        "emissions_factor_gco2_per_kwh",
        "radioactive_waste_g_per_kwh",
    ]:
        fmd[field] = pd.to_numeric(fmd[field], errors="coerce").fillna(0.0)

    disclosure_period = str(fmd["disclosure_period"].iloc[0])
    source_url = str(fmd["source_url"].iloc[0])
    source_date = str(fmd["source_date"].iloc[0])
    uk_average_factor = 154.0
    residual_factor = weighted_factor(fmd, "residual_mix_pct")
    uk_mix_proxy_factor = weighted_factor(fmd, "uk_average_mix_pct")
    radioactive_waste = float(fmd["radioactive_waste_g_per_kwh"].iloc[0])

    claims = read_claims()
    contract_rows: list[dict[str, object]] = []
    for claim in claims:
        contracted_mwh = float(claim["contracted_mwh"])
        uncovered_mwh = float(claim["uncovered_mwh"])
        contract_rows.append(
            {
                "customer_id": claim["customer_id"],
                "customer_name": claim["customer_name"],
                "contract_id": claim["contract_id"],
                "product_name": claim["product_name"],
                "disclosure_period": claim["disclosure_period"],
                "claim_status": claim["claim_status"],
                "contracted_mwh": round(contracted_mwh, 2),
                "uncovered_mwh": round(uncovered_mwh, 2),
                "location_based_emissions_proxy_tco2e": round(tco2e_from_mwh(contracted_mwh, uk_average_factor), 2),
                "uk_mix_attribute_context_tco2e": round(tco2e_from_mwh(contracted_mwh, uk_mix_proxy_factor), 2),
                "uncovered_residual_mix_context_tco2e": round(tco2e_from_mwh(uncovered_mwh, residual_factor), 2),
                "fmd_residual_factor_gco2_per_kwh": round(residual_factor, 2),
                "uk_generation_average_factor_gco2_per_kwh": round(uk_average_factor, 2),
                "fmd_uk_mix_proxy_factor_gco2_per_kwh": round(uk_mix_proxy_factor, 2),
                "methodology_note": "FMD and emissions values are reporting context only. They are not official customer Scope 2 emissions and do not determine REGO claim status.",
            }
        )

    summary = {
        "disclosure_period": disclosure_period,
        "data_period_start": "2024-04-01",
        "data_period_end": "2025-03-31",
        "source": "GOV.UK Fuel Mix Disclosure data table, 2024-2025",
        "source_url": source_url,
        "source_date": source_date,
        "uk_generation_average_factor_gco2_per_kwh": round(uk_average_factor, 2),
        "fmd_uk_mix_proxy_factor_gco2_per_kwh": round(uk_mix_proxy_factor, 2),
        "fmd_residual_factor_gco2_per_kwh": round(residual_factor, 2),
        "radioactive_waste_g_per_kwh": radioactive_waste,
        "uk_average_mix": {
            str(row["fuel_type"]): round(float(row["uk_average_mix_pct"]), 2)
            for _, row in fmd.iterrows()
        },
        "residual_mix": {
            str(row["fuel_type"]): round(float(row["residual_mix_pct"]), 2)
            for _, row in fmd.iterrows()
        },
        "methodology_note": "REGOs support contractual renewable claims and FMD evidence. Grid/FMD factors provide reporting context. This dashboard does not calculate an official customer Scope 2 inventory.",
        "contract_context": contract_rows,
    }
    return summary, contract_rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    summary, rows = build_context()
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(OUTPUT_CSV, rows)
    print(
        "FMD context built for "
        f"{summary['disclosure_period']}: residual factor "
        f"{summary['fmd_residual_factor_gco2_per_kwh']} gCO2/kWh."
    )


if __name__ == "__main__":
    main()
