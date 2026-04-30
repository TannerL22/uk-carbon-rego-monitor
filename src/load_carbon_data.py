"""Load and standardise carbon auction sample data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CARBON_RAW = ROOT / "data" / "raw" / "carbon"


def load_auction_data() -> pd.DataFrame:
    frames = []
    for filename in ["uka_auction_results_sample.csv", "eua_auction_results_sample.csv"]:
        path = CARBON_RAW / filename
        frame = pd.read_csv(path)
        frames.append(frame)

    auctions = pd.concat(frames, ignore_index=True)
    auctions["auction_date"] = pd.to_datetime(auctions["auction_date"], errors="coerce")
    for column in ["auction_volume", "clearing_price", "cover_ratio", "reference_price"]:
        auctions[column] = pd.to_numeric(auctions[column], errors="coerce")
    return auctions.sort_values(["auction_date", "market"]).reset_index(drop=True)
