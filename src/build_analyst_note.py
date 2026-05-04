"""Generate the analyst note from the current dashboard output."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "data" / "processed" / "dashboard_summary.json"
OUTPUT_PATH = ROOT / "outputs" / "analyst_note.md"


def money(value: object) -> str:
    return f"GBP {float(value):,.0f}"


def first_shortfalls(contracts: list[dict[str, object]]) -> list[dict[str, object]]:
    shortfalls = [item for item in contracts if float(item.get("shortfall_mwh", 0)) > 0]
    return sorted(shortfalls, key=lambda item: float(item.get("estimated_replacement_exposure_gbp", 0)), reverse=True)


def join_shortfall_sentence(shortfalls: list[dict[str, object]]) -> str:
    if not shortfalls:
        return "No contract has an eligible REGO shortfall in the current generated output."
    parts = [
        (
            f"{item['contract_id']} has a {float(item['shortfall_mwh']):,.0f} MWh shortfall "
            f"with {money(item['estimated_replacement_exposure_gbp'])} estimated cover cost"
        )
        for item in shortfalls
    ]
    return "; ".join(parts) + "."


def clean_sentence_fragment(value: object) -> str:
    text = str(value).strip().rstrip(".")
    if text.lower().startswith("latest auction demand:"):
        text = text.split(":", 1)[1].strip()
    return text[:1].upper() + text[1:] if text else text


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or f"{singular}s")


def present_verb(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def main() -> None:
    data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    carbon = data["carbon"]
    auction = data["auction"]
    power = data["power"]
    contracts = data["rego_contract_summary"]
    exceptions = data["rego_exceptions"]
    customer_claim_summary = data["customer_claim_summary"]
    scope2_readiness_summary = data["scope2_readiness_summary"]
    claim_evidence_summary = data["claim_evidence_summary"]
    fmd_context = data["fmd_context"]
    carbon_cost_context = data["carbon_cost_context"]
    source_quality = data["source_quality"]

    high_count = sum(1 for item in exceptions if item["severity"] == "High")
    medium_count = sum(1 for item in exceptions if item["severity"] == "Medium")
    low_count = sum(1 for item in exceptions if item["severity"] == "Low")
    shortfalls = first_shortfalls(contracts)
    total_shortfall = sum(float(item.get("shortfall_mwh", 0)) for item in contracts)
    total_exposure = sum(float(item.get("estimated_replacement_exposure_gbp", 0)) for item in contracts)
    covered = [item for item in contracts if item.get("coverage_status") in {"Covered", "Surplus"}]
    carbon_regime = clean_sentence_fragment(carbon["spread_regime"])
    auction_signal = clean_sentence_fragment(auction["demand_signal"])
    power_signal = clean_sentence_fragment(power["carbon_signal"])

    note = f"""# Analyst Note

## 1. Executive Summary

This monitor shows why carbon analysis for a renewables supplier is not limited to allowance prices. Auction data provides the compliance carbon-market signal, recent GB power-system data fetched at build time explains the physical emissions backdrop, and REGO reconciliation controls determine whether renewable supply claims can be evidenced against contracts and disclosure periods.

The generated dashboard is operational rather than purely market-facing. The carbon module shows {carbon_regime} over the comparison period {carbon['sample_period_start']} to {carbon['sample_period_end']}. The auction demand signal is {auction_signal.lower()}. The NESO power pull was fetched at build time and shows {power_signal.lower()}, with the main driver classified as {power['main_driver']}. Those context signals matter, but the main action sits in the customer claim book: {customer_claim_summary['contracts_not_supportable']} representative customer/product {pluralize(customer_claim_summary['contracts_not_supportable'], 'claim')} {present_verb(customer_claim_summary['contracts_not_supportable'], 'is', 'are')} not supportable, {customer_claim_summary['contracts_review']} {present_verb(customer_claim_summary['contracts_review'], 'requires', 'require')} review, and {customer_claim_summary['uncovered_mwh']:,.0f} MWh is uncovered.

## 2. Carbon Market Signal

The carbon-market module uses official EEX EUA primary-auction data, manually curated ICE UKA auction inputs, and the official GOV.UK UK ETS Cost Containment Mechanism monthly price table rather than licensed live price feeds. UKA prices are denominated in GBP and EUA prices are denominated in EUR, so the pipeline converts EUA prices into GBP using the stated static EUR/GBP assumption before calculating spread.

The latest generated comparison shows UKA at GBP {carbon['latest_uka_price_gbp']} and EUA at EUR {carbon['latest_eua_price_eur']}, equivalent to GBP {carbon['latest_eua_price_gbp']} using the stated FX assumption. The resulting UKA-EUA spread is GBP {carbon['latest_spread_gbp']}. This is a transparent auction-context indicator, not a live traded spread or a replacement for broker marks, exchange feeds, or internal trading data.

## 3. GB Power Fundamentals

The power-system module fetches recent data from the NESO Carbon Intensity API during the Python build. The dashboard compares the latest fetched carbon intensity of {power['latest_carbon_intensity_gco2_kwh']} g/kWh with a recent average of {power['average_recent_carbon_intensity_gco2_kwh']} g/kWh, and shows gas share, wind and solar share, low-carbon share, and scatter views linking generation mix to carbon intensity.

This matters because carbon-market commentary should be connected to physical system conditions. A higher-carbon generation mix may change the emissions context customers see, even though it is not the same thing as contractual renewable supply. Contractual renewable claims still depend on certificate ownership, eligibility, allocation, retirement, and disclosure evidence.

## 4. Customer Claim Coverage Findings

The claim coverage module is the commercial control layer. It reconciles representative customer/product claim contracts against eligible REGO evidence, contract coverage, excluded certificate volume, contract-scoped exceptions, and assumed replacement prices. Claim status is not affected by grid intensity or carbon prices; those are context layers only.

The customer claim coverage output shows {customer_claim_summary['uncovered_mwh']:,.0f} MWh uncovered, {customer_claim_summary['invalid_or_excluded_mwh']:,.0f} MWh invalid or excluded, and {money(customer_claim_summary['estimated_cover_cost_gbp'])} of assumed cover-cost exposure. The primary not-supportable claims are driven by contract-scoped high-severity evidence issues and uncovered eligible volume.

The claim evidence register converts control exceptions into an operational remediation workflow. It contains {claim_evidence_summary['register_items']} register items, including {claim_evidence_summary['open_items']} open items, {claim_evidence_summary['customer_impacting_items']} customer-impacting items, and {claim_evidence_summary['fmd_impacting_items']} FMD-impacting items. Each item carries an owner, status, target resolution date, source-evidence reference, impact label, and recommended remediation action.

The underlying REGO module remains the evidence engine. It reconciles representative demo certificate records against representative demo contracts for technology, country, generation vintage, lifecycle status, issue evidence, quantity fields, counterparty, source evidence, and contract ID validity. {join_shortfall_sentence(shortfalls)} Total eligible REGO shortfall is {total_shortfall:,.0f} MWh, with {money(total_exposure)} of assumed replacement-cost exposure. {len(covered)} {pluralize(len(covered), 'contract')} {('is' if len(covered) == 1 else 'are')} covered or in surplus in the current generated output.

The exception register contains {high_count} high, {medium_count} medium, and {low_count} low severity exceptions. It flags missing certificate IDs, duplicate IDs, invalid contract allocation, lifecycle errors, missing generation dates, missing issue dates, missing or invalid MWh quantities, technology mismatch, country mismatch, vintage mismatch, missing source file, stale available inventory, missing counterparty, retired certificates without retirement dates, and available certificates with allocation-date inconsistencies.

## 5. Operational Implications

The practical question is whether the supplier can evidence renewable delivery cleanly. The answer is mixed. The priority is to resolve high-severity certificate controls, replace ineligible or unsupported allocations, and source enough eligible certificates to cover open shortfalls before disclosure close.

The replacement-exposure calculation is deliberately simple: shortfall MWh multiplied by an assumed REGO replacement price in the contract file. It is not a market-price forecast, but it creates a clear pricing input for operational prioritisation.

The FMD layer adds disclosure-period context for {fmd_context['disclosure_period']}. It uses the GOV.UK FMD table to show a UK generation-average emissions factor of {fmd_context['uk_generation_average_factor_gco2_per_kwh']} gCO2/kWh and an FMD residual-mix context factor of {fmd_context['fmd_residual_factor_gco2_per_kwh']} gCO2/kWh. These values are used only as reporting context for contracted and uncovered MWh; they do not validate the renewable claim and they are not official customer Scope 2 emissions.

The future Scope 2 readiness layer is a data-preparedness view, not a compliance result. It separates current annual REGO claim supportability from possible future expectations around hourly matching and deliverability. The current output classifies {scope2_readiness_summary['high_readiness']} contracts as high readiness, {scope2_readiness_summary['medium_readiness']} as medium readiness, and {scope2_readiness_summary['low_readiness']} as low readiness. It does not apply final revised Scope 2 rules and it does not perform 24/7 matching.

The carbon-cost layer adds a market-cost lens without changing claim status. Using the latest generated UKA auction price of GBP {carbon_cost_context['latest_uka_price_gbp_per_tco2']} per tCO2, it converts selected emissions factors into indicative GBP/MWh values. For example, the FMD residual-mix context row is GBP {next(row['indicative_carbon_cost_gbp_per_mwh'] for row in carbon_cost_context['rows'] if row['factor_id'] == 'FMD_RESIDUAL_MIX')} per MWh. This is not a bill calculation, power-price forecast, or REGO claim validation input.

## 6. Data Limitations

The carbon data are official public or manually curated inputs, not licensed live UKA/EUA market data. The UKA auction CSV is not an automated ICE feed and should be checked against ICE Report Centre before external analytical use. The carbon spread uses a stated static EUR/GBP assumption and should not be read as a live traded spread. GOV.UK CCM monthly averages are policy and market context, not auction clearing prices.

The power data are fetched from the NESO Carbon Intensity API at build time, served as static dashboard output, and may be revised by the source. The REGO ledger and contracts are representative demo operating data because certificate-level supplier allocations and customer contract mappings are not public datasets. Source controls currently report {source_quality['warning_count']} warnings across {source_quality['sources_registered']} registered sources. Assumed replacement prices are illustrative. The monitor is not trading advice, legal advice, or compliance sign-off.
"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(note, encoding="utf-8")
    print(f"Analyst note written to {OUTPUT_PATH}.")


if __name__ == "__main__":
    main()
