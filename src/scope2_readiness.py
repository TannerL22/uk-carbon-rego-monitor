"""Assess future Scope 2 readiness separately from current REGO claim status."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "rego"
PROCESSED = ROOT / "data" / "processed"

CUSTOMER_CONTRACTS_PATH = RAW / "demo_customer_contracts.csv"
CLAIM_COVERAGE_PATH = PROCESSED / "customer_claim_coverage.json"
REGO_EXCEPTIONS_PATH = PROCESSED / "rego_exceptions.json"
READINESS_JSON_PATH = PROCESSED / "scope2_readiness.json"
READINESS_CSV_PATH = PROCESSED / "scope2_readiness.csv"
SUMMARY_PATH = PROCESSED / "scope2_readiness_summary.json"

MISSING_GENERATION_CONTROL = "RC-016"


def norm(value: object) -> str:
    return str(value or "").strip()


def yes(value: object) -> bool:
    return norm(value).lower() in {"yes", "y", "true", "1"}


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def primary_gap(
    current_status: str,
    market_boundary_available: bool,
    generation_data_available: bool,
    generation_gap_material: bool,
    hourly_available: bool,
    hourly_required: bool,
    deliverability_available: bool,
) -> str:
    if current_status == "Not supportable":
        return "Current annual claim is not supportable until REGO evidence issues are remediated."
    if not market_boundary_available:
        return "Market boundary is missing or unclear."
    if not generation_data_available and generation_gap_material:
        return "Material claimed evidence is missing generation-period data."
    if hourly_required and not hourly_available:
        return "Hourly matching requirement flagged, but settlement-period evidence is not available."
    if not hourly_available:
        return "Annual evidence is available, but hourly load/generation profiles are not available."
    if not deliverability_available:
        return "Deliverability boundary is not evidenced."
    return "No major readiness gap identified in the representative fields."


def readiness_status(
    current_status: str,
    market_boundary_available: bool,
    generation_data_available: bool,
    generation_gap_material: bool,
    hourly_available: bool,
    hourly_required: bool,
    deliverability_available: bool,
) -> str:
    if current_status == "Not supportable":
        return "Low"
    if not market_boundary_available:
        return "Low"
    if not generation_data_available and generation_gap_material:
        return "Low"
    if hourly_required and not hourly_available:
        return "Low"
    if not hourly_available or not deliverability_available or not generation_data_available:
        return "Medium"
    return "High"


def build_readiness() -> tuple[list[dict[str, object]], dict[str, object]]:
    if not CUSTOMER_CONTRACTS_PATH.exists():
        raise FileNotFoundError(f"Missing customer contract input: {CUSTOMER_CONTRACTS_PATH}")

    contracts = pd.read_csv(CUSTOMER_CONTRACTS_PATH, dtype=str).fillna("")
    contracts["contract_id_norm"] = contracts["contract_id"].astype(str).str.strip()
    coverage = {norm(row["contract_id"]): row for row in read_json(CLAIM_COVERAGE_PATH)}
    exceptions = [dict(row) for row in read_json(REGO_EXCEPTIONS_PATH)]

    rows: list[dict[str, object]] = []
    for _, contract in contracts.iterrows():
        contract_id = norm(contract["contract_id"])
        claim = coverage.get(contract_id, {})
        contract_exceptions = [item for item in exceptions if norm(item.get("contract_id")) == contract_id]
        missing_generation = [
            item for item in contract_exceptions if item.get("control_id") == MISSING_GENERATION_CONTROL
        ]

        current_status = norm(claim.get("claim_status")) or "Unknown"
        market_boundary_available = bool(norm(contract.get("market_boundary")))
        hourly_available = yes(contract.get("settlement_period_available"))
        hourly_required = yes(contract.get("hourly_matching_required"))
        deliverability_required = yes(contract.get("deliverability_required"))
        deliverability_available = (not deliverability_required) or market_boundary_available
        generation_data_available = not missing_generation
        invalid_mwh = float(claim.get("invalid_or_excluded_mwh", 0) or 0)
        materiality_mwh = float(claim.get("materiality_threshold_mwh", 0) or 0)
        generation_gap_material = bool(missing_generation) and invalid_mwh > materiality_mwh

        gap = primary_gap(
            current_status,
            market_boundary_available,
            generation_data_available,
            generation_gap_material,
            hourly_available,
            hourly_required,
            deliverability_available,
        )
        status = readiness_status(
            current_status,
            market_boundary_available,
            generation_data_available,
            generation_gap_material,
            hourly_available,
            hourly_required,
            deliverability_available,
        )

        rows.append(
            {
                "customer_id": norm(contract["customer_id"]),
                "customer_name": norm(contract["customer_name"]),
                "contract_id": contract_id,
                "product_name": norm(contract["product_name"]),
                "current_annual_claim_status": current_status,
                "future_scope2_readiness": status,
                "generation_period_data_available": generation_data_available,
                "market_boundary_available": market_boundary_available,
                "market_boundary": norm(contract.get("market_boundary")),
                "grid_region": norm(contract.get("grid_region")),
                "load_period_granularity": norm(contract.get("load_period_granularity")),
                "generation_period_granularity": norm(contract.get("generation_period_granularity")),
                "hourly_data_available": hourly_available,
                "hourly_matching_required": hourly_required,
                "deliverability_required": deliverability_required,
                "deliverability_boundary_available": deliverability_available,
                "legacy_claim_basis": norm(contract.get("legacy_claim_basis")),
                "primary_readiness_gap": gap,
                "methodology_note": "Future Scope 2 readiness is separate from current annual REGO claim supportability. It flags data-model preparedness only; it does not apply final Scope 2 rules or perform 24/7 matching.",
            }
        )

    summary = {
        "contracts_assessed": len(rows),
        "high_readiness": sum(1 for row in rows if row["future_scope2_readiness"] == "High"),
        "medium_readiness": sum(1 for row in rows if row["future_scope2_readiness"] == "Medium"),
        "low_readiness": sum(1 for row in rows if row["future_scope2_readiness"] == "Low"),
        "hourly_data_available_count": sum(1 for row in rows if row["hourly_data_available"]),
        "generation_period_data_available_count": sum(1 for row in rows if row["generation_period_data_available"]),
        "market_boundary_available_count": sum(1 for row in rows if row["market_boundary_available"]),
        "methodology_note": "This readiness layer is consultation-aware but not a compliance calculation. Current annual claim status remains governed by REGO evidence and contract controls.",
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    rows, summary = build_readiness()
    READINESS_JSON_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(READINESS_CSV_PATH, rows)
    print(
        "Scope 2 readiness assessed "
        f"{summary['contracts_assessed']} contracts: "
        f"{summary['high_readiness']} high, "
        f"{summary['medium_readiness']} medium, "
        f"{summary['low_readiness']} low."
    )


if __name__ == "__main__":
    main()
