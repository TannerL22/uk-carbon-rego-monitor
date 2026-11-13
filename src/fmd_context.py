"""Build FMD and emissions-reporting context for customer claims."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import pandas as pd


from project_paths import ROOT


RAW = ROOT / "data" / "raw" / "fmd"
PROCESSED = ROOT / "data" / "processed"

CLAIM_COVERAGE = PROCESSED / "customer_claim_coverage.json"
OUTPUT_JSON = PROCESSED / "fmd_context.json"
OUTPUT_CSV = PROCESSED / "fmd_context.csv"
NUMERIC_FIELDS = [
    "uk_average_mix_pct",
    "residual_mix_pct",
    "emissions_factor_gco2_per_kwh",
    "uk_generation_average_factor_gco2_per_kwh",
    "radioactive_waste_g_per_kwh",
]


def read_claims() -> list[dict[str, object]]:
    with CLAIM_COVERAGE.open(encoding="utf-8") as handle:
        return json.load(handle)


def weighted_factor(rows: pd.DataFrame, mix_column: str) -> float:
    return float((rows[mix_column] * rows["emissions_factor_gco2_per_kwh"]).sum() / 100)


def tco2e_from_mwh(mwh: object, factor_gco2_per_kwh: float) -> float:
    return float(mwh) * factor_gco2_per_kwh / 1000


def load_tables() -> dict[str, pd.DataFrame]:
    """Load every ``fmd_<start>_<end>.csv`` table keyed by disclosure period (e.g. "2024-25")."""

    tables: dict[str, pd.DataFrame] = {}
    for path in sorted(RAW.glob("fmd_*.csv")):
        table = pd.read_csv(path)
        for field in NUMERIC_FIELDS:
            if field in table:
                table[field] = pd.to_numeric(table[field], errors="coerce")
        if table["uk_generation_average_factor_gco2_per_kwh"].isna().any():
            raise ValueError(f"{path.name} is missing uk_generation_average_factor_gco2_per_kwh.")
        table["input_file"] = path.name
        tables[str(table["disclosure_period"].iloc[0])] = table
    if not tables:
        raise FileNotFoundError(f"No FMD input tables found in {RAW}. Run python src/fetch_fmd.py.")
    return tables


def period_bounds(period: str) -> tuple[str, str]:
    start_year = int(period[:4])
    return f"{start_year}-04-01", f"{start_year + 1}-03-31"


def period_factors(period: str, table: pd.DataFrame) -> dict[str, object]:
    start, end = period_bounds(period)
    factors = dict(zip(table["fuel_type"], table["emissions_factor_gco2_per_kwh"]))
    return {
        "disclosure_period": period,
        "data_period_start": start,
        "data_period_end": end,
        "source": f"GOV.UK Fuel Mix Disclosure data table, {period}",
        "source_url": str(table["source_url"].iloc[0]),
        "source_date": str(table["source_date"].iloc[0]),
        "input_file": str(table["input_file"].iloc[0]),
        "uk_generation_average_factor_gco2_per_kwh": round(float(table["uk_generation_average_factor_gco2_per_kwh"].iloc[0]), 2),
        "fmd_uk_mix_proxy_factor_gco2_per_kwh": round(weighted_factor(table, "uk_average_mix_pct"), 2),
        "fmd_residual_factor_gco2_per_kwh": round(weighted_factor(table, "residual_mix_pct"), 2),
        "natural_gas_factor_gco2_per_kwh": None if "Natural Gas" not in factors else round(float(factors["Natural Gas"]), 2),
        "radioactive_waste_g_per_kwh": float(table["radioactive_waste_g_per_kwh"].iloc[0]),
        "uk_average_mix": {str(row["fuel_type"]): round(float(row["uk_average_mix_pct"]), 2) for _, row in table.iterrows()},
        "residual_mix": {str(row["fuel_type"]): round(float(row["residual_mix_pct"]), 2) for _, row in table.iterrows()},
    }


def build_context() -> tuple[dict[str, object], list[dict[str, object]]]:
    tables = load_tables()
    factors_by_period = {period: period_factors(period, table) for period, table in tables.items()}
    latest_period = max(factors_by_period)

    claims = read_claims()
    claim_periods = Counter(str(claim["disclosure_period"]) for claim in claims)
    # Headline context follows the period most contracts disclose against.
    headline_period = claim_periods.most_common(1)[0][0] if claim_periods else latest_period
    if headline_period not in factors_by_period:
        headline_period = latest_period

    contract_rows: list[dict[str, object]] = []
    for claim in claims:
        claim_period = str(claim["disclosure_period"])
        matched = claim_period in factors_by_period
        factors = factors_by_period[claim_period if matched else latest_period]
        contracted_mwh = float(claim["contracted_mwh"])
        uncovered_mwh = float(claim["uncovered_mwh"])
        contract_rows.append(
            {
                "customer_id": claim["customer_id"],
                "customer_name": claim["customer_name"],
                "contract_id": claim["contract_id"],
                "product_name": claim["product_name"],
                "disclosure_period": claim_period,
                "fmd_table_period": factors["disclosure_period"],
                "fmd_period_matched": matched,
                "claim_status": claim["claim_status"],
                "contracted_mwh": round(contracted_mwh, 2),
                "uncovered_mwh": round(uncovered_mwh, 2),
                "location_based_emissions_proxy_tco2e": round(tco2e_from_mwh(contracted_mwh, factors["uk_generation_average_factor_gco2_per_kwh"]), 2),
                "uk_mix_attribute_context_tco2e": round(tco2e_from_mwh(contracted_mwh, factors["fmd_uk_mix_proxy_factor_gco2_per_kwh"]), 2),
                "uncovered_residual_mix_context_tco2e": round(tco2e_from_mwh(uncovered_mwh, factors["fmd_residual_factor_gco2_per_kwh"]), 2),
                "fmd_residual_factor_gco2_per_kwh": factors["fmd_residual_factor_gco2_per_kwh"],
                "uk_generation_average_factor_gco2_per_kwh": factors["uk_generation_average_factor_gco2_per_kwh"],
                "fmd_uk_mix_proxy_factor_gco2_per_kwh": factors["fmd_uk_mix_proxy_factor_gco2_per_kwh"],
                "methodology_note": "FMD and emissions values are reporting context only. They are not official customer Scope 2 emissions and do not determine REGO claim status.",
            }
        )

    summary = {
        **factors_by_period[headline_period],
        "periods_available": sorted(factors_by_period),
        "latest_period": factors_by_period[latest_period],
        "unmatched_contract_periods": sorted({row["disclosure_period"] for row in contract_rows if not row["fmd_period_matched"]}),
        "methodology_note": "REGOs support contractual renewable claims and FMD evidence. Grid/FMD factors provide reporting context, matched to each contract's disclosure period. This dashboard does not calculate an official customer Scope 2 inventory.",
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
