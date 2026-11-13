"""Validate source register completeness and freshness."""

from __future__ import annotations

import json

import pandas as pd

from project_paths import ROOT


INPUT = ROOT / "data" / "source_register.csv"
OUTPUT = ROOT / "data" / "processed" / "source_quality_summary.json"
CARBON_RAW = ROOT / "data" / "raw" / "carbon"
UKA_AUCTIONS = CARBON_RAW / "uka_auction_results.csv"
CCM_PRICES = CARBON_RAW / "uk_ets_ccm_monthly_prices.csv"
FX_ASSUMPTIONS = CARBON_RAW / "fx_assumptions.csv"
CARBON_SIGNALS = ROOT / "data" / "processed" / "carbon_signals.json"
BUILD_STATUS = ROOT / "data" / "processed" / "build_status.json"
# UKA auction clearing prices normally sit close to the same month's futures average.
UKA_CROSS_CHECK_TOLERANCE_PCT = 10.0
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


def uka_cross_check(issues: list[dict[str, object]]) -> None:
    """SC-008: compare UKA auction prices with the official GOV.UK monthly average for the same month."""

    if not UKA_AUCTIONS.exists() or not CCM_PRICES.exists():
        return
    uka = pd.read_csv(UKA_AUCTIONS)
    ccm = pd.read_csv(CCM_PRICES, dtype={"month": str})
    if "price_month" not in ccm.columns:
        ccm["price_month"] = (pd.PeriodIndex(ccm["month"], freq="M") - 1).astype(str)
    reference = (
        ccm.assign(official=pd.to_numeric(ccm["monthly_average_price"], errors="coerce"))
        .dropna(subset=["official"])
        .drop_duplicates("price_month", keep="last")
        .set_index("price_month")["official"]
    )
    uka = uka.assign(
        price_month=pd.to_datetime(uka["auction_date"], errors="coerce").dt.to_period("M").astype(str),
        clearing_price=pd.to_numeric(uka["clearing_price"], errors="coerce"),
    )
    uka["official"] = uka["price_month"].map(reference)
    checked = uka.dropna(subset=["clearing_price", "official"])
    if checked.empty:
        return
    deviation = (checked["clearing_price"] / checked["official"] - 1) * 100
    breaches = checked[deviation.abs() > UKA_CROSS_CHECK_TOLERANCE_PCT]
    if breaches.empty:
        return
    worst = deviation.abs().max()
    add_issue(
        issues,
        "SRC-003",
        "UKA auction results",
        "SC-008",
        "High",
        "clearing_price",
        (
            f"{len(breaches)} of {len(checked)} UKA auction prices deviate more than {UKA_CROSS_CHECK_TOLERANCE_PCT:.0f}% "
            f"from the official GOV.UK monthly average (max {worst:.0f}%)."
        ),
        "Re-curate the UKA auction CSV from ICE Report Centre; UKA price signals use GOV.UK monthly averages meanwhile.",
    )


def fx_validity_check(issues: list[dict[str, object]]) -> None:
    """SC-009: months converted with the static FX fallback should fall inside its validity window."""

    if not FX_ASSUMPTIONS.exists() or not CARBON_SIGNALS.exists():
        return
    fx = pd.read_csv(FX_ASSUMPTIONS)
    fx = fx[fx["currency_pair"] == "EURGBP"]
    if fx.empty:
        return
    carbon = json.loads(CARBON_SIGNALS.read_text(encoding="utf-8"))
    fallback_months = carbon.get("fx", {}).get("fallback_months", [])
    valid_from = pd.Period(str(fx.iloc[0]["valid_from"])[:7], freq="M")
    valid_to = pd.Period(str(fx.iloc[0]["valid_to"])[:7], freq="M")
    outside = [month for month in fallback_months if not valid_from <= pd.Period(month, freq="M") <= valid_to]
    if not outside:
        return
    add_issue(
        issues,
        "SRC-006",
        "EUR/GBP FX assumption",
        "SC-009",
        "Medium",
        "valid_from/valid_to",
        (
            f"Static EUR/GBP fallback (valid {valid_from} to {valid_to}) was used for {len(outside)} month(s) "
            f"outside that window ({', '.join(outside)}) because ECB rates were unavailable."
        ),
        "Check the ECB EUR/GBP fetch (src/fetch_ecb_fx.py) or update data/raw/carbon/fx_assumptions.csv.",
    )


def build_status_check(issues: list[dict[str, object]]) -> None:
    """SC-010: surface fetch steps that failed during this build (previous extract retained)."""

    if not BUILD_STATUS.exists():
        return
    status = json.loads(BUILD_STATUS.read_text(encoding="utf-8"))
    for failure in status.get("failed_steps", []):
        add_issue(
            issues,
            str(failure.get("source_id", "")),
            str(failure.get("dataset") or failure.get("step", "")),
            "SC-010",
            "High",
            "fetch",
            f"Public-source fetch failed during the latest build; the previous extract was retained. {failure.get('error', '')}".strip(),
            "Check the GitHub Actions refresh log and fix the fetch script before relying on this source's freshness.",
        )


def main() -> None:
    register = pd.read_csv(INPUT, dtype=str).fillna("")
    issues: list[dict[str, object]] = []
    latest_download = pd.to_datetime(register["downloaded_at"], errors="coerce", utc=True, format="mixed").max()
    stale_cutoff = latest_download - pd.Timedelta(days=120) if pd.notna(latest_download) else pd.Timestamp("2025-03-31", tz="UTC")

    for _, row in register.iterrows():
        source_id = row["source_id"]
        dataset_name = row["dataset_name"]
        source_type = row["source_type"].lower()
        source_url = row["source_url"].strip()
        downloaded_at = row["downloaded_at"].strip()
        period_start = pd.to_datetime(row["data_period_start"], errors="coerce", utc=True, format="mixed")
        period_end = pd.to_datetime(row["data_period_end"], errors="coerce", utc=True, format="mixed")

        source_exempt_from_url = any(token in source_type for token in ["synthetic", "representative demo", "assumption"])
        if not source_url and not source_exempt_from_url:
            add_issue(issues, source_id, dataset_name, "SC-001", "Medium", "source_url", "Missing source URL.", "Add the public source URL or document why none is available.")
        if not downloaded_at:
            add_issue(issues, source_id, dataset_name, "SC-002", "Medium", "downloaded_at", "Missing download timestamp.", "Populate downloaded_at for source lineage.")
        if pd.isna(period_start) or pd.isna(period_end):
            add_issue(issues, source_id, dataset_name, "SC-003", "Medium", "data_period_start/data_period_end", "Missing data period.", "Add the covered data period.")
        # Archived extracts of superseded official tables cannot be refreshed, so they are exempt.
        source_exempt_from_freshness = any(token in source_type for token in ["representative demo", "assumption", "archived"])
        if downloaded_at and not source_exempt_from_freshness:
            downloaded_dt = pd.to_datetime(downloaded_at, errors="coerce", utc=True, format="mixed")
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

    uka_cross_check(issues)
    fx_validity_check(issues)
    build_status_check(issues)

    counts = register.shape[0]
    severity_counts = {severity: sum(1 for issue in issues if issue["severity"] == severity) for severity in ["High", "Medium", "Low"]}
    output = {
        "sources_registered": int(counts),
        "warning_count": len(issues),
        "stale_source_count": sum(1 for issue in issues if issue["control_id"] == "SC-004"),
        "manual_sources_requiring_notes": sum(1 for issue in issues if issue["control_id"] == "SC-005"),
        "failed_fetch_count": sum(1 for issue in issues if issue["control_id"] == "SC-010"),
        "severity_counts": severity_counts,
        "issues": issues,
        "summary_signal": f"{len(issues)} source-register warnings",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Source controls produced {len(issues)} warnings.")


if __name__ == "__main__":
    main()
