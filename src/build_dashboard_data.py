"""Combine processed outputs into dashboard_summary.json."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = PROCESSED / "dashboard_summary.json"


def read_json(filename: str) -> object:
    with (PROCESSED / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


def read_optional_json(filename: str, default: object) -> object:
    path = PROCESSED / filename
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def money(value: float) -> str:
    return f"GBP {value:,.0f}"


def card(label: str, headline: str, subline: str) -> dict[str, str]:
    return {"label": label, "headline": headline, "subline": subline, "value": headline}


def short_carbon_headline(regime: str) -> str:
    return regime.replace("UKA ", "").replace(" than recent average", "")


def power_context_attention(power: dict[str, object]) -> str:
    signal = str(power["carbon_signal"]).replace("Carbon intensity ", "")
    driver = str(power["main_driver"])
    if "below" in signal:
        return f"GB power context: carbon intensity is {signal}, reducing near-term emissions-pressure signal."
    if "above" in signal:
        return f"GB power context: carbon intensity is {signal}, driven by {driver}."
    return f"GB power context: carbon intensity is {signal}, driven by {driver}."


def build_attention(
    carbon: dict[str, object],
    auction: dict[str, object],
    power: dict[str, object],
    contracts: list[dict[str, object]],
    exceptions: list[dict[str, object]],
    source_quality: dict[str, object],
) -> list[str]:
    items: list[str] = []
    shortfalls = [contract for contract in contracts if float(contract["shortfall_mwh"]) > 0]
    shortfalls.sort(key=lambda item: float(item["estimated_replacement_exposure_gbp"]), reverse=True)
    for contract in shortfalls[:2]:
        items.append(
            f"Contract {contract['contract_id']} has a {float(contract['shortfall_mwh']):,.0f} MWh eligible REGO shortfall "
            f"with {money(float(contract['estimated_replacement_exposure_gbp']))} estimated cover cost."
        )

    high_exceptions = [item for item in exceptions if item["severity"] == "High"]
    if high_exceptions:
        items.append(f"{len(high_exceptions)} high-severity certificate exceptions require review before disclosure close.")
    if source_quality["warning_count"]:
        items.append(f"{source_quality['warning_count']} source-register warnings require documentation clean-up.")
    items.append(str(carbon["spread_regime"]) + ".")
    if str(auction["demand_signal"]).lower().endswith("insufficient"):
        items.append("Auction demand data are insufficient for a firm demand signal.")
    power_item = power_context_attention(power)
    items.append(power_item)
    deduped = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped[:6]


def main() -> None:
    carbon = read_json("carbon_signals.json")
    market_reference = read_optional_json(
        "carbon_market_reference.json",
        {
            "available": False,
            "enabled": False,
            "provider": "Trading Economics",
            "label": "Third-party market reference",
            "note": "Optional third-party market reference not loaded.",
            "series": [],
        },
    )
    auction = read_json("auction_signals.json")
    power = read_json("power_signals.json")
    contracts = read_json("rego_contract_summary.json")
    exceptions = read_json("rego_exceptions.json")
    source_quality = read_json("source_quality_summary.json")

    latest_ci = float(power["latest_carbon_intensity_gco2_kwh"])
    recent_ci = float(power["average_recent_carbon_intensity_gco2_kwh"])
    total_shortfall = sum(float(contract["shortfall_mwh"]) for contract in contracts)
    total_exposure = sum(float(contract["estimated_replacement_exposure_gbp"]) for contract in contracts)
    high_count = sum(1 for exception in exceptions if exception["severity"] == "High")

    carbon["market_reference"] = market_reference

    summary = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "data_basis": [
            {"label": "Carbon market", "value": "Official/manual auction + CCM context"},
            {"label": "Power", "value": "NESO Carbon Intensity API"},
            {"label": "REGO controls", "value": "Representative demo supplier-style ledger"},
            {"label": "Contracts", "value": "Representative demo contracts"},
        ],
        "cards": [
            card("Carbon market signal", short_carbon_headline(str(carbon["spread_regime"])), f"UKA-EUA spread GBP {carbon['latest_spread_gbp']}; {carbon['sample_period_start']} to {carbon['sample_period_end']}"),
            card("Auction demand", "Neutral", f"Latest UKA cover ratio {auction['latest_uka_cover_ratio']} vs {auction['trailing_uka_cover_ratio']} recent avg"),
            card("GB power signal", str(power["carbon_signal"]).replace("Carbon intensity ", "").capitalize(), f"{latest_ci:.0f} g/kWh vs {recent_ci:.0f} g/kWh recent avg"),
            card("REGO controls", f"{len(exceptions)} exceptions", f"{high_count} high severity; review before disclosure close"),
            card("Contract exposure", f"{total_shortfall:,.0f} MWh shortfall", f"{money(total_exposure)} estimated cover cost"),
            card("Data quality", f"{source_quality['warning_count']} warnings", f"{source_quality['sources_registered']} sources registered"),
        ],
        "analyst_attention": build_attention(carbon, auction, power, contracts, exceptions, source_quality),
        "carbon": carbon,
        "auction": auction,
        "power": power,
        "rego_contract_summary": contracts,
        "rego_exceptions": exceptions,
        "source_quality": source_quality,
        "analyst_note_path": "outputs/analyst_note.md",
    }

    OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Dashboard summary written to {OUTPUT}.")


if __name__ == "__main__":
    main()
