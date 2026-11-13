"""Calculate UKA/EUA carbon-market signals on an official monthly basis.

UKA price: GOV.UK UK ETS Cost Containment Mechanism (CCM) monthly average
futures price (official, published by DESNZ / UK ETS Authority).
EUA price: volume-weighted monthly average of official EEX EU ETS1 primary
auction clearing prices, converted to GBP with the stated static FX assumption.

Both legs are official public data and refresh automatically, so the spread
stays current without depending on the manually maintained UKA auction CSV.
"""

from __future__ import annotations

import json

import pandas as pd

from load_carbon_data import load_auction_data
from project_paths import ROOT


OUTPUT = ROOT / "data" / "processed" / "carbon_signals.json"
FX_PATH = ROOT / "data" / "raw" / "carbon" / "fx_assumptions.csv"
CCM_PATH = ROOT / "data" / "raw" / "carbon" / "uk_ets_ccm_monthly_prices.csv"

TRAILING_MONTHS = 6
MIN_TRAILING_MONTHS = 3
SERIES_MONTHS = 24
Z_SCORE_THRESHOLD = 1.0


def classify_spread(z_score: float, latest_spread: float) -> str:
    if z_score > Z_SCORE_THRESHOLD:
        return "UKA discount narrower than recent average" if latest_spread < 0 else "UKA premium wider than recent average"
    if z_score < -Z_SCORE_THRESHOLD:
        return "UKA discount wider than recent average" if latest_spread < 0 else "UKA premium narrower than recent average"
    if latest_spread < 0:
        return "UKA discount broadly stable"
    return "UKA premium broadly stable"


def load_fx_assumption() -> dict[str, object]:
    assumptions = pd.read_csv(FX_PATH)
    eur_gbp = assumptions[assumptions["currency_pair"] == "EURGBP"]
    if eur_gbp.empty:
        raise ValueError("Missing EURGBP FX assumption in data/raw/carbon/fx_assumptions.csv")
    row = eur_gbp.iloc[0]
    return {
        "currency_pair": str(row["currency_pair"]),
        "rate": float(row["rate"]),
        "rate_basis": str(row["rate_basis"]),
        "valid_from": str(row["valid_from"]),
        "valid_to": str(row["valid_to"]),
        "source": str(row["source"]),
        "notes": str(row["notes"]),
    }


def load_ccm_table() -> pd.DataFrame:
    """Load the GOV.UK CCM table with a ``price_month`` column.

    Each CCM row is labelled with its assessment month; the final average price
    in the row belongs to the month before (the end of the monitoring window).
    """

    if not CCM_PATH.exists():
        return pd.DataFrame()
    ccm = pd.read_csv(CCM_PATH, dtype={"month": str})
    if ccm.empty:
        return ccm
    if "price_month" not in ccm.columns:
        ccm["price_month"] = (pd.PeriodIndex(ccm["month"], freq="M") - 1).astype(str)
    ccm["monthly_average_price"] = pd.to_numeric(ccm["monthly_average_price"], errors="coerce")
    ccm["trigger_price"] = pd.to_numeric(ccm["trigger_price"], errors="coerce")
    return ccm.sort_values("month").reset_index(drop=True)


def monthly_eua_prices(auctions: pd.DataFrame) -> pd.DataFrame:
    """Volume-weighted monthly average of EUA auction clearing prices (EUR)."""

    eua = auctions[(auctions["market"] == "EUA")].dropna(subset=["auction_date", "clearing_price", "auction_volume"])
    if eua.empty:
        raise ValueError("Carbon signal requires EUA auction rows.")
    eua = eua.assign(
        price_month=eua["auction_date"].dt.to_period("M").astype(str),
        price_x_volume=eua["clearing_price"] * eua["auction_volume"],
    )
    grouped = eua.groupby("price_month").agg(
        price_x_volume=("price_x_volume", "sum"),
        auction_volume=("auction_volume", "sum"),
        eua_auction_count=("clearing_price", "size"),
    )
    grouped["EUA"] = grouped["price_x_volume"] / grouped["auction_volume"]
    return grouped[["EUA", "eua_auction_count"]].reset_index()


def build_monthly_spread(ccm: pd.DataFrame, eua_monthly: pd.DataFrame, fx_rate: float) -> pd.DataFrame:
    uka = (
        ccm.dropna(subset=["monthly_average_price"])
        .drop_duplicates("price_month", keep="last")
        .rename(columns={"monthly_average_price": "UKA"})[["price_month", "UKA"]]
    )
    merged = uka.merge(eua_monthly, on="price_month", how="inner").sort_values("price_month").reset_index(drop=True)
    if merged.empty:
        raise ValueError("No month has both a GOV.UK UKA monthly average and EEX EUA auction prices.")
    merged["EUA_GBP"] = merged["EUA"] * fx_rate
    merged["spread_gbp"] = merged["UKA"] - merged["EUA_GBP"]
    # Trailing statistics use the months *before* each row so the latest value is
    # compared against history rather than against a window that includes itself.
    prior = merged["spread_gbp"].shift(1).rolling(window=TRAILING_MONTHS, min_periods=MIN_TRAILING_MONTHS)
    merged["trailing_average_spread_gbp"] = prior.mean()
    merged["trailing_std_spread_gbp"] = prior.std()
    return merged


def spread_z_score(latest: pd.Series) -> float:
    average = latest["trailing_average_spread_gbp"]
    std = latest["trailing_std_spread_gbp"]
    if pd.isna(average) or pd.isna(std) or not std:
        return 0.0
    return float((latest["spread_gbp"] - average) / std)


def optional_round(value: object) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), 2)


def build_ccm_context(ccm: pd.DataFrame) -> dict[str, object]:
    if ccm.empty:
        return {"available": False, "note": "GOV.UK UK ETS CCM monthly price table has not been fetched.", "series": []}

    completed = ccm.dropna(subset=["monthly_average_price"])
    latest_row = ccm.iloc[-1] if completed.empty else completed.iloc[-1]
    upcoming = ccm[ccm["month"] > str(latest_row["month"])]
    next_trigger = upcoming.iloc[0] if not upcoming.empty else None
    series = [
        {
            "month": str(row["price_month"]),
            "assessment_month": str(row["month"]),
            "monthly_average_price_gbp": optional_round(row["monthly_average_price"]),
            "trigger_price_gbp": optional_round(row["trigger_price"]),
            "ccm_triggered": str(row["ccm_triggered"]),
            "monitoring_window_months": int(row["monitoring_window_months"]),
        }
        for _, row in completed.tail(18).iterrows()
    ]
    return {
        "available": True,
        "latest_month": str(latest_row["price_month"]),
        "latest_assessment_month": str(latest_row["month"]),
        "latest_monthly_average_price_gbp": optional_round(latest_row["monthly_average_price"]),
        "latest_trigger_price_gbp": optional_round(latest_row["trigger_price"]),
        "latest_ccm_triggered": str(latest_row["ccm_triggered"]),
        "next_assessment_month": None if next_trigger is None else str(next_trigger["month"]),
        "next_trigger_price_gbp": None if next_trigger is None else optional_round(next_trigger["trigger_price"]),
        "monitoring_window_months": int(latest_row["monitoring_window_months"]),
        "source_url": str(latest_row["source_url"]),
        "downloaded_at": str(latest_row["downloaded_at"]),
        "published_at": str(latest_row["published_at"]),
        "note": (
            "Official GOV.UK UK ETS CCM monthly average futures price. latest_month is the calendar month the "
            "average covers (the CCM row for the following assessment month); not an auction clearing price "
            "and not a live trading feed."
        ),
        "series": series,
    }


def main() -> None:
    fx = load_fx_assumption()
    ccm = load_ccm_table()
    if ccm.empty or ccm["monthly_average_price"].dropna().empty:
        raise FileNotFoundError("GOV.UK CCM monthly prices are missing. Run python src/fetch_uk_ets_ccm.py first.")

    monthly = build_monthly_spread(ccm, monthly_eua_prices(load_auction_data()), float(fx["rate"]))
    latest = monthly.iloc[-1]
    z_score = spread_z_score(latest)
    regime = classify_spread(z_score, float(latest["spread_gbp"]))
    window = monthly.tail(SERIES_MONTHS)
    start, end = str(window["price_month"].iloc[0]), str(window["price_month"].iloc[-1])

    series = [
        {
            "date": str(row["price_month"]),
            "uka_price_gbp": round(float(row["UKA"]), 2),
            "eua_price_eur": round(float(row["EUA"]), 2),
            "eua_price_gbp": round(float(row["EUA_GBP"]), 2),
            "spread_gbp": round(float(row["spread_gbp"]), 2),
            "eua_auction_count": int(row["eua_auction_count"]),
            "trailing_average_spread_gbp": optional_round(row["trailing_average_spread_gbp"]),
        }
        for _, row in window.iterrows()
    ]

    output = {
        "price_basis": "monthly",
        "latest_price_month": str(latest["price_month"]),
        "sample_period_start": start,
        "sample_period_end": end,
        "sample_period_label": f"Carbon market comparison period: {start} to {end} (monthly averages)",
        "latest_uka_price_gbp": round(float(latest["UKA"]), 2),
        "latest_eua_price_eur": round(float(latest["EUA"]), 2),
        "latest_eua_price_gbp": round(float(latest["EUA_GBP"]), 2),
        "latest_spread_gbp": round(float(latest["spread_gbp"]), 2),
        "trailing_average_spread_gbp": optional_round(latest["trailing_average_spread_gbp"]),
        "spread_z_score": round(z_score, 2),
        "spread_regime": regime,
        "fx_assumption": fx,
        "currency_note": (
            f"EUA EUR auction prices are converted to GBP using a static EUR/GBP assumption of {float(fx['rate']):.2f}. "
            "The resulting UKA-EUA spread is shown in GBP and is a transparent monthly context indicator, not a live traded spread."
        ),
        "basis_note": (
            "UKA = official GOV.UK UK ETS CCM monthly average futures price. EUA = volume-weighted monthly average of "
            "official EEX EU ETS1 primary auction clearing prices. Months are compared only when both are published."
        ),
        "uka_ccm_context": build_ccm_context(ccm),
        "limitation": (
            "Carbon market data uses official public monthly averages and auction results rather than licensed live "
            "UKA/EUA price feeds; the futures-average and auction-average legs are not identical instruments."
        ),
        "series": series,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Carbon signal ({end}): {regime}; spread GBP {output['latest_spread_gbp']}.")


if __name__ == "__main__":
    main()
