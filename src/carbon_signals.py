"""Calculate UKA/EUA carbon-market signals."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from load_carbon_data import load_auction_data


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "carbon_signals.json"
FX_PATH = ROOT / "data" / "raw" / "carbon" / "fx_assumptions.csv"


def classify_spread(z_score: float, latest_spread: float) -> str:
    if z_score > 1.0:
        return "UKA premium wider than recent average"
    if z_score < -1.0:
        return "UKA discount wider than recent average"
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


def align_uka_eua_auctions(auctions: pd.DataFrame) -> pd.DataFrame:
    """Align UKA auctions with the nearest EUA auction within a 14-day window."""

    uka = (
        auctions[auctions["market"] == "UKA"]
        .sort_values("auction_date")
        .rename(columns={"auction_date": "uka_auction_date", "clearing_price": "UKA"})
    )
    eua = (
        auctions[auctions["market"] == "EUA"]
        .sort_values("auction_date")
        .rename(columns={"auction_date": "eua_auction_date", "clearing_price": "EUA"})
    )
    if uka.empty or eua.empty:
        raise ValueError("Carbon signal requires both UKA and EUA auction rows.")

    aligned = pd.merge_asof(
        uka,
        eua,
        left_on="uka_auction_date",
        right_on="eua_auction_date",
        direction="nearest",
        tolerance=pd.Timedelta(days=14),
        suffixes=("_uka", "_eua"),
    ).dropna(subset=["UKA", "EUA", "eua_auction_date"])

    if aligned.empty:
        raise ValueError("No UKA auctions could be aligned to EUA auctions within 14 days.")

    aligned["auction_date"] = aligned["uka_auction_date"]
    aligned = aligned.set_index("auction_date")
    return aligned


def main() -> None:
    auctions = load_auction_data()
    fx = load_fx_assumption()
    aligned = align_uka_eua_auctions(auctions)
    aligned["EUA_GBP"] = aligned["EUA"] * float(fx["rate"])
    aligned["spread_gbp"] = aligned["UKA"] - aligned["EUA_GBP"]
    aligned["trailing_average_spread_gbp"] = aligned["spread_gbp"].rolling(window=6, min_periods=3).mean()
    aligned["trailing_std_spread_gbp"] = aligned["spread_gbp"].rolling(window=6, min_periods=3).std()
    latest = aligned.iloc[-1]
    trailing_average = float(latest["trailing_average_spread_gbp"])
    trailing_std = float(latest["trailing_std_spread_gbp"]) if pd.notna(latest["trailing_std_spread_gbp"]) and latest["trailing_std_spread_gbp"] else 0.0
    z_score = (float(latest["spread_gbp"]) - trailing_average) / trailing_std if trailing_std else 0.0
    regime = classify_spread(z_score, float(latest["spread_gbp"]))

    series = [
        {
            "date": idx.date().isoformat(),
            "uka_price_gbp": round(float(row["UKA"]), 2),
            "eua_price_eur": round(float(row["EUA"]), 2),
            "eua_price_gbp": round(float(row["EUA_GBP"]), 2),
            "spread_gbp": round(float(row["spread_gbp"]), 2),
            "eua_auction_date": row["eua_auction_date"].date().isoformat(),
            "trailing_average_spread_gbp": None
            if pd.isna(row["trailing_average_spread_gbp"])
            else round(float(row["trailing_average_spread_gbp"]), 2),
        }
        for idx, row in aligned.iterrows()
    ]
    sample_period_start = aligned.index.min().date().isoformat()
    sample_period_end = aligned.index.max().date().isoformat()

    output = {
        "latest_auction_date": aligned.index[-1].date().isoformat(),
        "sample_period_start": sample_period_start,
        "sample_period_end": sample_period_end,
        "sample_period_label": f"Carbon market comparison period: {sample_period_start} to {sample_period_end}",
        "latest_uka_price_gbp": round(float(latest["UKA"]), 2),
        "latest_eua_price_eur": round(float(latest["EUA"]), 2),
        "latest_eua_price_gbp": round(float(latest["EUA_GBP"]), 2),
        "latest_spread_gbp": round(float(latest["spread_gbp"]), 2),
        "trailing_average_spread_gbp": round(trailing_average, 2),
        "spread_z_score": round(float(z_score), 2),
        "spread_regime": regime,
        "fx_assumption": fx,
        "currency_note": (
            f"EUA EUR auction prices are converted to GBP using a static EUR/GBP assumption of {float(fx['rate']):.2f}. "
            "The resulting UKA-EUA spread is shown in GBP and is a transparent auction-context indicator, not a live traded spread."
        ),
        "alignment_note": "UKA auction dates are compared with the nearest official EUA auction date within 14 days because UKA and EUA auction calendars differ.",
        "limitation": "Carbon market data uses official/public or curated auction inputs rather than licensed live UKA/EUA price feeds.",
        "series": series,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Carbon signal: {regime}.")


if __name__ == "__main__":
    main()
