"""Build customer renewable claim coverage outputs from REGO controls."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "rego"
PROCESSED = ROOT / "data" / "processed"

CUSTOMER_CONTRACTS_PATH = RAW / "demo_customer_contracts.csv"
REGO_SUMMARY_PATH = PROCESSED / "rego_contract_summary.json"
REGO_EXCEPTIONS_PATH = PROCESSED / "rego_exceptions.json"
COVERAGE_JSON_PATH = PROCESSED / "customer_claim_coverage.json"
COVERAGE_CSV_PATH = PROCESSED / "customer_claim_coverage.csv"
SUMMARY_PATH = PROCESSED / "customer_claim_summary.json"

CLAIM_BLOCKING_CONTROLS = {
    "RC-001",
    "RC-002",
    "RC-003",
    "RC-004",
    "RC-006",
    "RC-009",
    "RC-013",
    "RC-016",
    "RC-017",
    "RC-018",
    "RC-019",
}


def norm(value: object) -> str:
    return str(value or "").strip()


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def materiality_threshold(contract: pd.Series) -> float:
    contracted_mwh = float(contract["contracted_mwh"])
    threshold_mwh = float(contract["materiality_threshold_mwh"])
    threshold_pct = float(contract["materiality_threshold_pct"])
    return max(threshold_mwh, contracted_mwh * threshold_pct / 100)


def primary_issue(
    uncovered_mwh: float,
    materiality_mwh: float,
    blocking_exceptions: list[dict[str, object]],
    other_exceptions: list[dict[str, object]],
) -> str:
    if blocking_exceptions:
        first = blocking_exceptions[0]
        return f"{first['control_id']} {first['control_type']}"
    if uncovered_mwh > materiality_mwh:
        return "Material eligible REGO shortfall"
    if uncovered_mwh > 0:
        return "Immaterial eligible REGO shortfall"
    if other_exceptions:
        first = other_exceptions[0]
        return f"{first['control_id']} {first['control_type']}"
    return "No material claim issue"


def claim_status(
    coverage_pct: float,
    uncovered_mwh: float,
    materiality_mwh: float,
    invalid_or_excluded_mwh: float,
    blocking_exceptions: list[dict[str, object]],
    other_exceptions: list[dict[str, object]],
) -> str:
    material_shortfall = uncovered_mwh > materiality_mwh
    material_invalid = invalid_or_excluded_mwh > materiality_mwh
    if blocking_exceptions and (material_shortfall or material_invalid or coverage_pct < 100):
        return "Not supportable"
    if material_shortfall:
        return "Shortfall"
    if coverage_pct >= 100 and not blocking_exceptions and not other_exceptions:
        return "Covered"
    return "Review"


def build_coverage() -> tuple[list[dict[str, object]], dict[str, object]]:
    if not CUSTOMER_CONTRACTS_PATH.exists():
        raise FileNotFoundError(f"Missing customer claim contract input: {CUSTOMER_CONTRACTS_PATH}")

    customer_contracts = pd.read_csv(CUSTOMER_CONTRACTS_PATH, dtype=str).fillna("")
    customer_contracts["contract_id_norm"] = customer_contracts["contract_id"].astype(str).str.strip()
    for field in [
        "contracted_mwh",
        "replacement_price_gbp_per_mwh",
        "materiality_threshold_mwh",
        "materiality_threshold_pct",
    ]:
        customer_contracts[field] = pd.to_numeric(customer_contracts[field], errors="coerce").fillna(0.0)

    rego_summary = {norm(row["contract_id"]): row for row in read_json(REGO_SUMMARY_PATH)}
    exceptions = [dict(row) for row in read_json(REGO_EXCEPTIONS_PATH)]

    rows: list[dict[str, object]] = []
    for _, contract in customer_contracts.iterrows():
        contract_id = norm(contract["contract_id"])
        summary = rego_summary.get(contract_id, {})
        contract_exceptions = [item for item in exceptions if norm(item.get("contract_id")) == contract_id]
        blocking = [
            item
            for item in contract_exceptions
            if item.get("severity") == "High" and item.get("control_id") in CLAIM_BLOCKING_CONTROLS
        ]
        other = [item for item in contract_exceptions if item not in blocking and item.get("control_id") != "RC-015"]

        required_mwh = float(contract["contracted_mwh"])
        eligible_mwh = float(summary.get("eligible_matched_mwh", 0.0))
        invalid_or_excluded_mwh = float(summary.get("ineligible_allocated_mwh", 0.0))
        uncovered_mwh = max(required_mwh - eligible_mwh, 0.0)
        surplus_mwh = max(eligible_mwh - required_mwh, 0.0)
        coverage_pct = eligible_mwh / required_mwh * 100 if required_mwh else 0.0
        materiality_mwh = materiality_threshold(contract)
        replacement_price = float(contract["replacement_price_gbp_per_mwh"])
        estimated_cover_cost = uncovered_mwh * replacement_price
        status = claim_status(
            coverage_pct,
            uncovered_mwh,
            materiality_mwh,
            invalid_or_excluded_mwh,
            blocking,
            other,
        )
        issue = primary_issue(uncovered_mwh, materiality_mwh, blocking, other)

        rows.append(
            {
                "customer_id": norm(contract["customer_id"]),
                "customer_name": norm(contract["customer_name"]),
                "contract_id": contract_id,
                "product_name": norm(contract["product_name"]),
                "claim_type": norm(contract["claim_type"]),
                "claim_basis": norm(contract["claim_basis"]),
                "customer_claim_wording": norm(contract["customer_claim_wording"]),
                "delivery_period_start": norm(contract["delivery_period_start"]),
                "delivery_period_end": norm(contract["delivery_period_end"]),
                "disclosure_period": norm(contract["disclosure_period"]),
                "contracted_mwh": round(required_mwh, 2),
                "eligible_rego_mwh": round(eligible_mwh, 2),
                "coverage_pct": round(coverage_pct, 2),
                "uncovered_mwh": round(uncovered_mwh, 2),
                "surplus_mwh": round(surplus_mwh, 2),
                "invalid_or_excluded_mwh": round(invalid_or_excluded_mwh, 2),
                "replacement_price_gbp_per_mwh": round(replacement_price, 2),
                "estimated_cover_cost_gbp": round(estimated_cover_cost, 2),
                "materiality_threshold_mwh": round(materiality_mwh, 2),
                "high_claim_blocking_exception_count": len(blocking),
                "exception_count": len(contract_exceptions),
                "claim_status": status,
                "primary_issue": issue,
                "claim_owner": norm(contract["claim_owner"]),
                "technology_requirement": norm(contract["technology_requirement"]),
                "country_requirement": norm(contract["country_requirement"]),
                "methodology_note": "Claim status is based on eligible REGO evidence, contract coverage, and contract-scoped exceptions only. Grid intensity and carbon prices are context layers and do not determine claim validity.",
            }
        )

    summary = {
        "contracts_assessed": len(rows),
        "contracts_covered": sum(1 for row in rows if row["claim_status"] == "Covered"),
        "contracts_review": sum(1 for row in rows if row["claim_status"] == "Review"),
        "contracts_shortfall": sum(1 for row in rows if row["claim_status"] == "Shortfall"),
        "contracts_not_supportable": sum(1 for row in rows if row["claim_status"] == "Not supportable"),
        "uncovered_mwh": round(sum(float(row["uncovered_mwh"]) for row in rows), 2),
        "invalid_or_excluded_mwh": round(sum(float(row["invalid_or_excluded_mwh"]) for row in rows), 2),
        "estimated_cover_cost_gbp": round(sum(float(row["estimated_cover_cost_gbp"]) for row in rows), 2),
        "claim_blocking_exception_count": sum(int(row["high_claim_blocking_exception_count"]) for row in rows),
        "methodology_note": "REGO evidence determines claim supportability. FMD, NESO, Scope 2, and UK ETS signals provide context only.",
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
    rows, summary = build_coverage()
    COVERAGE_JSON_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(COVERAGE_CSV_PATH, rows)
    print(
        "Customer claim coverage assessed "
        f"{summary['contracts_assessed']} contracts: "
        f"{summary['contracts_not_supportable']} not supportable, "
        f"{summary['contracts_review']} review, "
        f"{summary['contracts_shortfall']} shortfall, "
        f"{summary['contracts_covered']} covered."
    )


if __name__ == "__main__":
    main()
