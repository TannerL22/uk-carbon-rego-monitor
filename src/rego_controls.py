"""Run REGO certificate controls and contract reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "rego"
PROCESSED = ROOT / "data" / "processed"

CONTRACTS_PATH = RAW / "synthetic_contracts.csv"
LEDGER_PATH = RAW / "synthetic_rego_ledger.csv"
EXCEPTIONS_PATH = PROCESSED / "rego_exceptions.json"
SUMMARY_PATH = PROCESSED / "rego_contract_summary.json"

DATE_FIELDS = [
    "generation_start",
    "generation_end",
    "issue_date",
    "received_date",
    "allocated_date",
    "retired_date",
    "last_updated",
]

CONTROL_GROUPS = {
    "RC-001": "Missing certificate ID",
    "RC-002": "Duplicate certificate ID",
    "RC-003": "Lifecycle status conflict",
    "RC-004": "Impossible lifecycle date",
    "RC-005": "Missing contract ID",
    "RC-006": "Invalid contract ID",
    "RC-007": "Technology mismatch",
    "RC-008": "Country mismatch",
    "RC-009": "Vintage outside delivery period",
    "RC-010": "Missing source file",
    "RC-011": "Stale available certificate",
    "RC-012": "Missing counterparty",
    "RC-013": "Retired without retirement date",
    "RC-014": "Status/date inconsistency",
    "RC-015": "Contract shortfall",
}


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    for path in [CONTRACTS_PATH, LEDGER_PATH]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing REGO demo input {path}. "
                "Run python src/seed_demo_data.py to intentionally reset representative demo inputs."
            )
    contracts = pd.read_csv(CONTRACTS_PATH, dtype=str).fillna("")
    ledger = pd.read_csv(LEDGER_PATH, dtype=str).fillna("")

    contracts["required_mwh"] = pd.to_numeric(contracts["required_mwh"], errors="coerce").fillna(0.0)
    contracts["assumed_rego_replacement_price_gbp_per_mwh"] = pd.to_numeric(
        contracts["assumed_rego_replacement_price_gbp_per_mwh"], errors="coerce"
    ).fillna(0.0)
    ledger["quantity_mwh"] = pd.to_numeric(ledger["quantity_mwh"], errors="coerce").fillna(0.0)

    for field in ["contract_start", "contract_end", "delivery_period_start", "delivery_period_end"]:
        contracts[f"{field}_dt"] = pd.to_datetime(contracts[field], errors="coerce")
    for field in DATE_FIELDS:
        ledger[f"{field}_dt"] = pd.to_datetime(ledger[field], errors="coerce")

    return contracts, ledger


def add_exception(
    exceptions: list[dict[str, object]],
    control_id: str,
    severity: str,
    row: pd.Series | None,
    field: str,
    observed_value: object,
    expected_value: object,
    exception_message: str,
    suggested_action: str,
    contract_id: str | None = None,
) -> None:
    exceptions.append(
        {
            "exception_id": f"EX-{len(exceptions) + 1:04d}",
            "control_id": control_id,
            "control_type": CONTROL_GROUPS[control_id],
            "severity": severity,
            "certificate_id": "" if row is None else str(row.get("certificate_id", "")),
            "contract_id": contract_id if contract_id is not None else ("" if row is None else str(row.get("contract_id", ""))),
            "field": field,
            "observed_value": "" if observed_value is None else str(observed_value),
            "expected_value": "" if expected_value is None else str(expected_value),
            "exception_message": exception_message,
            "suggested_action": suggested_action,
        }
    )


def is_allocated(row: pd.Series) -> bool:
    status = str(row.get("status", "")).strip().lower()
    return bool(str(row.get("allocated_date", "")).strip() or str(row.get("contract_id", "")).strip() or status in {"allocated", "retired"})


def technology_matches(certificate_technology: str, eligible_technology: str) -> bool:
    if eligible_technology.strip().lower() == "any renewable":
        return certificate_technology.strip().lower() in {"wind", "solar", "hydro", "biomass"}
    return certificate_technology.strip().lower() == eligible_technology.strip().lower()


def run_certificate_controls(contracts: pd.DataFrame, ledger: pd.DataFrame) -> tuple[list[dict[str, object]], set[int]]:
    exceptions: list[dict[str, object]] = []
    invalid_indexes: set[int] = set()
    contract_ids = set(contracts["contract_id"])
    contract_lookup = contracts.set_index("contract_id").to_dict("index")

    cert_ids = ledger["certificate_id"].astype(str).str.strip()
    duplicate_ids = set(cert_ids[(cert_ids != "") & cert_ids.duplicated(keep=False)])
    analysis_date = ledger["last_updated_dt"].max()
    stale_cutoff = analysis_date - pd.Timedelta(days=90) if pd.notna(analysis_date) else pd.Timestamp("2025-03-31")

    for idx, row in ledger.iterrows():
        certificate_id = str(row.get("certificate_id", "")).strip()
        contract_id = str(row.get("contract_id", "")).strip()
        status = str(row.get("status", "")).strip()
        allocated = is_allocated(row)
        high_or_eligibility_failure = False

        if not certificate_id:
            add_exception(
                exceptions,
                "RC-001",
                "High",
                row,
                "certificate_id",
                certificate_id,
                "Non-blank unique certificate ID",
                "Certificate record is missing its certificate ID.",
                "Obtain the original certificate reference before using the record for disclosure or allocation.",
            )
            high_or_eligibility_failure = True

        if certificate_id in duplicate_ids:
            add_exception(
                exceptions,
                "RC-002",
                "High",
                row,
                "certificate_id",
                certificate_id,
                "Unique certificate ID",
                "Certificate ID appears more than once in the ledger.",
                "Investigate duplicate ledger entries and remove any double-counted allocation.",
            )
            high_or_eligibility_failure = True

        if status.lower() == "available" and str(row.get("retired_date", "")).strip():
            add_exception(
                exceptions,
                "RC-003",
                "High",
                row,
                "status",
                f"status={status}; retired_date={row.get('retired_date', '')}",
                "Available certificate should not have a retirement date",
                "Certificate is marked available even though a retirement date is populated.",
                "Reconcile the certificate lifecycle status with the registry record.",
            )
            high_or_eligibility_failure = True

        retired_dt = row.get("retired_date_dt")
        issue_dt = row.get("issue_date_dt")
        if pd.notna(retired_dt) and pd.notna(issue_dt) and retired_dt < issue_dt:
            add_exception(
                exceptions,
                "RC-004",
                "High",
                row,
                "retired_date",
                row.get("retired_date", ""),
                f">= issue_date {row.get('issue_date', '')}",
                "Retirement date is before the certificate issue date.",
                "Correct date fields before relying on the certificate for evidence.",
            )
            high_or_eligibility_failure = True

        if allocated and not contract_id:
            add_exception(
                exceptions,
                "RC-005",
                "Medium",
                row,
                "contract_id",
                contract_id,
                "Allocated records should reference a contract",
                "Allocated certificate is missing a contract ID.",
                "Add the contract reference or move the certificate back to unallocated inventory.",
            )
            high_or_eligibility_failure = True

        if contract_id and contract_id not in contract_ids:
            add_exception(
                exceptions,
                "RC-006",
                "High",
                row,
                "contract_id",
                contract_id,
                "Contract ID present in contract file",
                "Certificate allocation references a contract that is not in the contract file.",
                "Confirm whether the contract exists and update the contract master before allocation.",
            )
            high_or_eligibility_failure = True

        if contract_id in contract_lookup:
            contract = contract_lookup[contract_id]
            if not technology_matches(str(row.get("technology", "")), str(contract["eligible_technology"])):
                add_exception(
                    exceptions,
                    "RC-007",
                    "Medium",
                    row,
                    "technology",
                    row.get("technology", ""),
                    contract["eligible_technology"],
                    "Certificate technology does not match contract eligibility.",
                    "Review product claim and reallocate to an eligible certificate batch if needed.",
                )
                high_or_eligibility_failure = True

            if str(row.get("country", "")).strip().lower() != str(contract["eligible_country"]).strip().lower():
                add_exception(
                    exceptions,
                    "RC-008",
                    "Medium",
                    row,
                    "country",
                    row.get("country", ""),
                    contract["eligible_country"],
                    "Certificate country does not match contract eligibility.",
                    "Check disclosure rules and replace with an eligible certificate if required.",
                )
                high_or_eligibility_failure = True

            gen_start = row.get("generation_start_dt")
            gen_end = row.get("generation_end_dt")
            delivery_start = contract["delivery_period_start_dt"]
            delivery_end = contract["delivery_period_end_dt"]
            if pd.notna(gen_start) and pd.notna(gen_end) and (gen_start < delivery_start or gen_end > delivery_end):
                add_exception(
                    exceptions,
                    "RC-009",
                    "High",
                    row,
                    "generation_start/generation_end",
                    f"{row.get('generation_start', '')} to {row.get('generation_end', '')}",
                    f"{contract['delivery_period_start']} to {contract['delivery_period_end']}",
                    "Certificate generation period is outside the contract delivery period.",
                    "Remove from contract coverage or obtain eligible vintage certificates.",
                )
                high_or_eligibility_failure = True

        if not str(row.get("source_file", "")).strip():
            add_exception(
                exceptions,
                "RC-010",
                "Low",
                row,
                "source_file",
                row.get("source_file", ""),
                "Source file reference populated",
                "Certificate record is missing a source file reference.",
                "Populate source lineage to support audit review.",
            )

        if status.lower() == "available" and pd.notna(row.get("last_updated_dt")) and row["last_updated_dt"] < stale_cutoff:
            add_exception(
                exceptions,
                "RC-011",
                "Medium",
                row,
                "last_updated",
                row.get("last_updated", ""),
                f">= {stale_cutoff.date()}",
                "Available certificate has not been updated recently.",
                "Refresh inventory status and confirm whether the certificate remains available.",
            )

        if allocated and not str(row.get("counterparty", "")).strip():
            add_exception(
                exceptions,
                "RC-012",
                "Medium",
                row,
                "counterparty",
                row.get("counterparty", ""),
                "Allocated records should include counterparty",
                "Allocated certificate is missing counterparty detail.",
                "Add counterparty information from the contract or allocation record.",
            )
            high_or_eligibility_failure = True

        if status.lower() == "retired" and not str(row.get("retired_date", "")).strip():
            add_exception(
                exceptions,
                "RC-013",
                "High",
                row,
                "retired_date",
                row.get("retired_date", ""),
                "Retired certificates should include retirement date",
                "Certificate is marked retired without a retirement date.",
                "Update retirement evidence before using the certificate in disclosure.",
            )
            high_or_eligibility_failure = True

        if status.lower() == "available" and str(row.get("allocated_date", "")).strip():
            add_exception(
                exceptions,
                "RC-014",
                "Medium",
                row,
                "status/allocated_date",
                f"status={status}; allocated_date={row.get('allocated_date', '')}",
                "Available certificates should not have allocation date",
                "Certificate is available but has an allocation date populated.",
                "Confirm whether the certificate is allocated or available and correct the status fields.",
            )
            high_or_eligibility_failure = True

        if high_or_eligibility_failure:
            invalid_indexes.add(idx)

    return exceptions, invalid_indexes


def build_contract_summary(
    contracts: pd.DataFrame,
    ledger: pd.DataFrame,
    invalid_indexes: set[int],
    exceptions: list[dict[str, object]],
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    duplicate_ids = set(ledger["certificate_id"][ledger["certificate_id"].astype(str).str.strip().duplicated(keep=False)])

    for _, contract in contracts.iterrows():
        contract_id = contract["contract_id"]
        allocated = ledger[ledger["contract_id"] == contract_id].copy()
        eligible_mask = []
        for idx, row in allocated.iterrows():
            lifecycle_ok = idx not in invalid_indexes
            cert_id = str(row.get("certificate_id", "")).strip()
            contract_ok = bool(cert_id) and cert_id not in duplicate_ids
            tech_ok = technology_matches(str(row.get("technology", "")), str(contract["eligible_technology"]))
            country_ok = str(row.get("country", "")).strip().lower() == str(contract["eligible_country"]).strip().lower()
            vintage_ok = (
                pd.notna(row["generation_start_dt"])
                and pd.notna(row["generation_end_dt"])
                and row["generation_start_dt"] >= contract["delivery_period_start_dt"]
                and row["generation_end_dt"] <= contract["delivery_period_end_dt"]
            )
            status_ok = str(row.get("status", "")).strip().lower() in {"allocated", "retired"}
            eligible_mask.append(lifecycle_ok and contract_ok and tech_ok and country_ok and vintage_ok and status_ok)

        allocated = allocated.assign(is_eligible=eligible_mask)
        required_mwh = float(contract["required_mwh"])
        eligible_mwh = float(allocated.loc[allocated["is_eligible"], "quantity_mwh"].sum())
        allocated_mwh = float(allocated["quantity_mwh"].sum())
        ineligible_mwh = max(allocated_mwh - eligible_mwh, 0.0)
        shortfall_mwh = max(required_mwh - eligible_mwh, 0.0)
        surplus_mwh = max(eligible_mwh - required_mwh, 0.0)
        price = float(contract["assumed_rego_replacement_price_gbp_per_mwh"])
        exposure = shortfall_mwh * price
        if shortfall_mwh > 0:
            status = "Shortfall"
        elif surplus_mwh > 0:
            status = "Surplus"
        elif ineligible_mwh > 0:
            status = "Review"
        else:
            status = "Covered"
        coverage_ratio = eligible_mwh / required_mwh if required_mwh else 0.0

        summary = {
            "contract_id": contract_id,
            "counterparty": contract["counterparty"],
            "product_type": contract["product_type"],
            "required_mwh": round(required_mwh, 2),
            "eligible_matched_mwh": round(eligible_mwh, 2),
            "ineligible_allocated_mwh": round(ineligible_mwh, 2),
            "shortfall_mwh": round(shortfall_mwh, 2),
            "surplus_mwh": round(surplus_mwh, 2),
            "coverage_ratio": round(coverage_ratio, 4),
            "assumed_rego_replacement_price_gbp_per_mwh": round(price, 2),
            "estimated_replacement_exposure_gbp": round(exposure, 2),
            "coverage_status": status,
            "fmd_period": contract["fmd_period"],
        }
        summaries.append(summary)

        if shortfall_mwh > 0:
            add_exception(
                exceptions,
                "RC-015",
                "High",
                None,
                "eligible_matched_mwh",
                round(eligible_mwh, 2),
                required_mwh,
                f"Contract {contract_id} has an eligible REGO shortfall of {shortfall_mwh:,.0f} MWh.",
                "Source eligible replacement REGOs or update allocation before disclosure close.",
                contract_id=contract_id,
            )

    return summaries


def severity_rank(exception: dict[str, object]) -> tuple[int, str]:
    order = {"High": 0, "Medium": 1, "Low": 2}
    return order.get(str(exception["severity"]), 9), str(exception["control_id"])


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    contracts, ledger = read_inputs()
    exceptions, invalid_indexes = run_certificate_controls(contracts, ledger)
    contract_summary = build_contract_summary(contracts, ledger, invalid_indexes, exceptions)
    exceptions.sort(key=severity_rank)

    with EXCEPTIONS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(exceptions, handle, indent=2)
    with SUMMARY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(contract_summary, handle, indent=2)

    print(f"REGO controls produced {len(exceptions)} exceptions across {len(contract_summary)} contracts.")


if __name__ == "__main__":
    main()
