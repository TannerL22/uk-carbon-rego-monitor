"""Validate source register completeness and freshness."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "source_register.csv"
OUTPUT = ROOT / "data" / "processed" / "source_quality_summary.json"
ANALYSIS_START = pd.Timestamp("2024-04-01", tz="UTC")
ANALYSIS_END = pd.Timestamp("2025-03-31", tz="UTC")


def add_issue(
    issues: list[dict[str, object]],
    source_id: str,
    dataset_name: str,
    control_id: str,
    severity: str,
    field: str,
    issue: str,
    suggested_action: str,
) -> None:
    issues.append(
        {
            "issue_id": f"SRC-EX-{len(issues) + 1:03d}",
            "source_id": source_id,
            "dataset_name": dataset_name,
            "control_id": control_id,
            "severity": severity,
            "field": field,
            "issue": issue,
            "suggested_action": suggested_action,
        }
    )


def main() -> None:
    register = pd.read_csv(INPUT, dtype=str).fillna("")
    issues: list[dict[str, object]] = []
    latest_download = pd.to_datetime(register["downloaded_at"], errors="coerce", utc=True).max()
    stale_cutoff = latest_download - pd.Timedelta(days=120) if pd.notna(latest_download) else pd.Timestamp("2025-03-31", tz="UTC")

    for _, row in register.iterrows():
        source_id = row["source_id"]
        dataset_name = row["dataset_name"]
        source_type = row["source_type"].lower()
        source_url = row["source_url"].strip()
        downloaded_at = row["downloaded_at"].strip()
        period_start = pd.to_datetime(row["data_period_start"], errors="coerce", utc=True)
        period_end = pd.to_datetime(row["data_period_end"], errors="coerce", utc=True)

        source_exempt_from_url = any(token in source_type for token in ["synthetic", "representative demo", "assumption"])
        if not source_url and not source_exempt_from_url:
            add_issue(issues, source_id, dataset_name, "SC-001", "Medium", "source_url", "Missing source URL.", "Add the public source URL or document why none is available.")
        if not downloaded_at:
            add_issue(issues, source_id, dataset_name, "SC-002", "Medium", "downloaded_at", "Missing download timestamp.", "Populate downloaded_at for source lineage.")
        if pd.isna(period_start) or pd.isna(period_end):
            add_issue(issues, source_id, dataset_name, "SC-003", "Medium", "data_period_start/data_period_end", "Missing data period.", "Add the covered data period.")
        source_exempt_from_freshness = any(token in source_type for token in ["representative demo", "assumption"])
        if downloaded_at and not source_exempt_from_freshness:
            downloaded_dt = pd.to_datetime(downloaded_at, errors="coerce", utc=True)
            if pd.notna(downloaded_dt) and downloaded_dt < stale_cutoff:
                add_issue(issues, source_id, dataset_name, "SC-004", "Low", "downloaded_at", "Source download is stale versus latest registered source.", "Refresh the sample or note why the older extract remains valid.")
        if row["manual_or_api"].strip().lower() == "manual" and not row["known_limitations"].strip():
            add_issue(issues, source_id, dataset_name, "SC-005", "Medium", "known_limitations", "Manual input lacks limitations note.", "Add limitations or review note for the manual source.")
        if not row["source_owner"].strip():
            add_issue(issues, source_id, dataset_name, "SC-006", "Low", "source_owner", "Missing source owner.", "Populate the source owner.")
        used_for = row["used_for"].strip().lower()
        requires_rego_period = "rego" in used_for or "contract" in used_for
        if requires_rego_period and pd.notna(period_start) and pd.notna(period_end) and (period_end < ANALYSIS_START or period_start > ANALYSIS_END):
            add_issue(
                issues,
                source_id,
                dataset_name,
                "SC-007",
                "Medium",
                "data_period_start/data_period_end",
                "Data period does not overlap the REGO analysis period.",
                "Confirm whether this source is intended as market context or update period coverage.",
            )

    counts = register.shape[0]
    severity_counts = {severity: sum(1 for issue in issues if issue["severity"] == severity) for severity in ["High", "Medium", "Low"]}
    output = {
        "sources_registered": int(counts),
        "warning_count": len(issues),
        "stale_source_count": sum(1 for issue in issues if issue["control_id"] == "SC-004"),
        "manual_sources_requiring_notes": sum(1 for issue in issues if issue["control_id"] == "SC-005"),
        "severity_counts": severity_counts,
        "issues": issues,
        "summary_signal": f"{len(issues)} source-register warnings",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Source controls produced {len(issues)} warnings.")


if __name__ == "__main__":
    main()
