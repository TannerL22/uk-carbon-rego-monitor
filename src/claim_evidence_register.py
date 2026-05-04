"""Build a claim evidence and remediation register from REGO controls."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "rego"
PROCESSED = ROOT / "data" / "processed"

LEDGER_PATH = RAW / "synthetic_rego_ledger.csv"
CLAIM_COVERAGE_PATH = PROCESSED / "customer_claim_coverage.json"
EXCEPTIONS_PATH = PROCESSED / "rego_exceptions.json"
REGISTER_JSON_PATH = PROCESSED / "claim_evidence_register.json"
REGISTER_CSV_PATH = PROCESSED / "claim_evidence_register.csv"
SUMMARY_PATH = PROCESSED / "claim_evidence_summary.json"

CUSTOMER_IMPACTING_CONTROLS = {
    "RC-001",
    "RC-002",
    "RC-003",
    "RC-004",
    "RC-006",
    "RC-007",
    "RC-008",
    "RC-009",
    "RC-013",
    "RC-015",
    "RC-016",
    "RC-017",
    "RC-018",
    "RC-019",
}
FMD_IMPACTING_CONTROLS = {
    "RC-001",
    "RC-002",
    "RC-003",
    "RC-004",
    "RC-006",
    "RC-008",
    "RC-009",
    "RC-010",
    "RC-013",
    "RC-015",
    "RC-016",
    "RC-017",
    "RC-018",
    "RC-019",
}
CONTROL_ACTIONS = {
    "RC-001": "Obtain the missing certificate reference before relying on the record.",
    "RC-002": "Investigate duplicate certificate records and remove any double-counted allocation.",
    "RC-003": "Reconcile lifecycle status against the registry record.",
    "RC-004": "Correct lifecycle dates or replace the certificate evidence.",
    "RC-005": "Populate the contract allocation or remove the certificate from claimed volume.",
    "RC-006": "Confirm the contract master record before treating the allocation as valid.",
    "RC-007": "Replace or reallocate the certificate to match the product technology requirement.",
    "RC-008": "Replace or reallocate the certificate to match the eligible country requirement.",
    "RC-009": "Replace with certificates generated inside the contract delivery period.",
    "RC-010": "Attach source-file evidence to support audit traceability.",
    "RC-011": "Review stale available inventory and refresh registry status.",
    "RC-012": "Populate counterparty evidence for the allocation trail.",
    "RC-013": "Populate retirement date or verify the retirement status.",
    "RC-014": "Correct allocation/status date fields before disclosure use.",
    "RC-015": "Procure or reallocate eligible REGOs to cover the contract shortfall.",
    "RC-016": "Request usable generation-period dates or replace the evidence.",
    "RC-017": "Request issue-date evidence from the registry/export source.",
    "RC-018": "Confirm quantity MWh before counting the certificate toward coverage.",
    "RC-019": "Correct quantity MWh or exclude the record from claimed volume.",
}


def norm(value: object) -> str:
    return str(value or "").strip()


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def target_resolution_date(disclosure_period: str, severity: str) -> str:
    parts = norm(disclosure_period).split("-")
    if len(parts) == 2 and parts[1].isdigit():
        close_year = 2000 + int(parts[1])
    else:
        close_year = 2025
    return f"{close_year}-09-15" if severity in {"High", "Medium"} else f"{close_year}-09-30"


def source_quality_score(source_file: str, control_id: str, severity: str) -> int:
    if control_id == "RC-010" or not norm(source_file):
        return 40
    if severity == "High":
        return 65
    if severity == "Medium":
        return 78
    return 90


def register_status(severity: str) -> str:
    if severity == "High":
        return "Open - action required"
    if severity == "Medium":
        return "Open - review required"
    return "Monitor"


def impact_label(control_id: str, claim: dict[str, object], severity: str) -> str:
    if control_id in CUSTOMER_IMPACTING_CONTROLS or claim.get("claim_status") in {"Not supportable", "Shortfall"}:
        return "Customer-impacting"
    if severity == "Medium":
        return "Potential customer impact"
    return "Housekeeping"


def fmd_impact_label(control_id: str, claim: dict[str, object]) -> str:
    if "fmd" in norm(claim.get("claim_type")).lower() or control_id in FMD_IMPACTING_CONTROLS:
        return "FMD-impacting"
    return "FMD documentation context"


def build_register() -> tuple[list[dict[str, object]], dict[str, object]]:
    ledger = pd.read_csv(LEDGER_PATH, dtype=str).fillna("")
    ledger["certificate_id_norm"] = ledger["certificate_id"].astype(str).str.strip()
    ledger_by_cert: dict[str, dict[str, object]] = {}
    for _, row in ledger.iterrows():
        certificate_id = norm(row.get("certificate_id_norm"))
        if certificate_id and certificate_id not in ledger_by_cert:
            ledger_by_cert[certificate_id] = row.to_dict()
    claims = {norm(row["contract_id"]): row for row in read_json(CLAIM_COVERAGE_PATH)}
    exceptions = [dict(row) for row in read_json(EXCEPTIONS_PATH)]

    rows: list[dict[str, object]] = []
    for item in exceptions:
        contract_id = norm(item.get("contract_id"))
        certificate_id = norm(item.get("certificate_id"))
        claim = claims.get(contract_id, {})
        ledger_row = ledger_by_cert.get(certificate_id, {})
        severity = norm(item.get("severity"))
        control_id = norm(item.get("control_id"))
        source_file = norm(ledger_row.get("source_file"))
        customer_impact = impact_label(control_id, claim, severity)
        fmd_impact = fmd_impact_label(control_id, claim)

        rows.append(
            {
                "evidence_register_id": f"ER-{len(rows) + 1:04d}",
                "exception_id": norm(item.get("exception_id")),
                "customer_id": norm(claim.get("customer_id")),
                "customer_name": norm(claim.get("customer_name")),
                "contract_id": contract_id,
                "product_name": norm(claim.get("product_name")),
                "certificate_id": certificate_id,
                "control_id": control_id,
                "control_type": norm(item.get("control_type")),
                "severity": severity,
                "evidence_source": "Representative demo REGO ledger",
                "source_file": source_file,
                "source_quality_score": source_quality_score(source_file, control_id, severity),
                "exception_owner": norm(claim.get("claim_owner")) or "Renewables Operations",
                "remediation_action": CONTROL_ACTIONS.get(control_id, norm(item.get("suggested_action"))),
                "target_resolution_date": target_resolution_date(norm(claim.get("disclosure_period")), severity),
                "customer_claim_impact": customer_impact,
                "fmd_impact": fmd_impact,
                "status": register_status(severity),
                "issue": norm(item.get("exception_message")),
                "methodology_note": "The evidence register translates certificate/control exceptions into owner, impact, and remediation fields. It is an operating workflow aid, not legal or compliance sign-off.",
            }
        )

    summary = {
        "register_items": len(rows),
        "open_items": sum(1 for row in rows if str(row["status"]).startswith("Open")),
        "customer_impacting_items": sum(1 for row in rows if row["customer_claim_impact"] == "Customer-impacting"),
        "fmd_impacting_items": sum(1 for row in rows if row["fmd_impact"] == "FMD-impacting"),
        "high_severity_items": sum(1 for row in rows if row["severity"] == "High"),
        "owners": sorted({row["exception_owner"] for row in rows if row["exception_owner"]}),
        "methodology_note": "Every material shortfall and high-severity control issue is carried into the evidence register with an owner, status, impact label, target date, and remediation action.",
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
    rows, summary = build_register()
    REGISTER_JSON_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(REGISTER_CSV_PATH, rows)
    print(
        "Claim evidence register built "
        f"{summary['register_items']} items: "
        f"{summary['open_items']} open, "
        f"{summary['customer_impacting_items']} customer-impacting."
    )


if __name__ == "__main__":
    main()
