"""Build indicative carbon-cost context from UKA and emissions factors."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT_JSON = PROCESSED / "carbon_cost_context.json"
OUTPUT_CSV = PROCESSED / "carbon_cost_context.csv"

UK_ETS_MARKETS_URL = "https://www.gov.uk/government/publications/taking-part-in-the-uk-emissions-trading-scheme-markets/taking-part-in-the-uk-emissions-trading-scheme-markets"


def read_json(filename: str) -> dict[str, object]:
    with (PROCESSED / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


def cost_per_mwh(uka_price_gbp_per_tco2: float, factor_gco2_per_kwh: float) -> float:
    return uka_price_gbp_per_tco2 * factor_gco2_per_kwh / 1000


def main() -> None:
    carbon = read_json("carbon_signals.json")
    fmd = read_json("fmd_context.json")

    uka_price = float(carbon["latest_uka_price_gbp"])
    ccm = carbon.get("uka_ccm_context", {})
    ccm_trigger = ccm.get("latest_trigger_price_gbp")
    ccm_trigger_value = None if ccm_trigger is None else float(ccm_trigger)
    auction_reserve_price = 28.0

    factor_rows = [
        {
            "factor_id": "UK_AVERAGE_GENERATION",
            "label": "UK generation average context",
            "emissions_factor_gco2_per_kwh": float(fmd["uk_generation_average_factor_gco2_per_kwh"]),
            "factor_basis": "GOV.UK FMD UK generation average factor",
        },
        {
            "factor_id": "FMD_RESIDUAL_MIX",
            "label": "FMD residual mix context",
            "emissions_factor_gco2_per_kwh": float(fmd["fmd_residual_factor_gco2_per_kwh"]),
            "factor_basis": "GOV.UK FMD residual mix context factor",
        },
        {
            "factor_id": "GAS_PROXY",
            "label": "Natural gas proxy",
            "emissions_factor_gco2_per_kwh": 382.0,
            "factor_basis": "GOV.UK FMD natural gas emissions factor proxy",
        },
    ]

    rows: list[dict[str, object]] = []
    for row in factor_rows:
        factor = float(row["emissions_factor_gco2_per_kwh"])
        rows.append(
            {
                **row,
                "uka_price_gbp_per_tco2": round(uka_price, 2),
                "indicative_carbon_cost_gbp_per_mwh": round(cost_per_mwh(uka_price, factor), 2),
                "auction_reserve_price_gbp_per_tco2": auction_reserve_price,
                "auction_reserve_price_cost_gbp_per_mwh": round(cost_per_mwh(auction_reserve_price, factor), 2),
                "ccm_trigger_price_gbp_per_tco2": None if ccm_trigger_value is None else round(ccm_trigger_value, 2),
                "ccm_trigger_context_gbp_per_mwh": None
                if ccm_trigger_value is None
                else round(cost_per_mwh(ccm_trigger_value, factor), 2),
            }
        )

    summary = {
        "label": "Indicative carbon-cost context",
        "latest_uka_price_gbp_per_tco2": round(uka_price, 2),
        "latest_uka_auction_date": carbon["latest_auction_date"],
        "auction_reserve_price_gbp_per_tco2": auction_reserve_price,
        "auction_reserve_price_effective_from": "2026-04-08",
        "auction_reserve_price_source_url": UK_ETS_MARKETS_URL,
        "ccm_latest_month": ccm.get("latest_month"),
        "ccm_trigger_price_gbp_per_tco2": None if ccm_trigger_value is None else round(ccm_trigger_value, 2),
        "fmd_disclosure_period": fmd["disclosure_period"],
        "rows": rows,
        "methodology_note": (
            "Indicative carbon cost per MWh = UKA GBP/tCO2 * emissions factor tCO2/MWh. "
            "This is market and fossil/residual exposure context only: not a bill calculation, not a power-price forecast, "
            "not a REGO claim validation input, and not an official customer emissions result."
        ),
    }

    OUTPUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Carbon-cost context built using UKA GBP {uka_price:.2f}/tCO2.")


if __name__ == "__main__":
    main()
