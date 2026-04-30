"""Calculate auction volume and demand signals."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from load_carbon_data import load_auction_data


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "auction_signals.json"


def demand_signal(latest_cover: float | None, trailing_cover: float | None) -> str:
    if latest_cover is None or trailing_cover is None or pd.isna(latest_cover) or pd.isna(trailing_cover):
        return "Auction demand data insufficient"
    if latest_cover > trailing_cover + 0.15:
        return "Latest auction demand stronger than recent average"
    if latest_cover < trailing_cover - 0.15:
        return "Latest auction demand weaker than recent average"
    return "Latest auction demand: neutral"


def main() -> None:
    auctions = load_auction_data()
    latest_date = auctions["auction_date"].max()
    next_auction_date = latest_date + pd.Timedelta(days=21)
    latest_rows = auctions[auctions["auction_date"] == latest_date]
    latest_uka = latest_rows[latest_rows["market"] == "UKA"].iloc[0]

    cover_series = auctions[auctions["market"] == "UKA"].sort_values("auction_date")["cover_ratio"]
    latest_cover = float(cover_series.iloc[-1]) if len(cover_series) else None
    trailing_cover = float(cover_series.tail(6).mean()) if len(cover_series.dropna()) >= 3 else None
    signal = demand_signal(latest_cover, trailing_cover)

    volume_series = auctions.groupby("auction_date")["auction_volume"].sum().reset_index()
    latest_volume = float(volume_series["auction_volume"].iloc[-1])
    trailing_volume = float(volume_series["auction_volume"].tail(6).mean())
    volume_signal = "Auction supply above recent average" if latest_volume > trailing_volume else "Auction supply near recent average"

    output = {
        "latest_auction_date": latest_date.date().isoformat(),
        "latest_uka_volume": int(latest_uka["auction_volume"]),
        "latest_uka_cover_ratio": latest_cover,
        "trailing_uka_cover_ratio": round(trailing_cover, 2) if trailing_cover is not None else None,
        "demand_signal": signal,
        "volume_signal": volume_signal,
        "next_auction_date": next_auction_date.date().isoformat(),
        "series": [
            {
                "date": row["auction_date"].date().isoformat(),
                "auction_volume": int(row["auction_volume"]),
            }
            for _, row in volume_series.iterrows()
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Auction signal: {signal}.")


if __name__ == "__main__":
    main()
