"""Load and standardise carbon auction input data.

Normal builds treat carbon auction CSVs as raw inputs. They are not generated
or overwritten by ``build_all.py``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CARBON_RAW = ROOT / "data" / "raw" / "carbon"
AUCTION_INPUTS = {
    "UKA": ["uka_auction_results.csv"],
    "EUA": ["eua_auction_results.csv", "eua_auction_results_sample.csv"],
}
REQUIRED_COLUMNS = {
    "market",
    "auction_date",
    "auction_volume",
    "clearing_price",
    "currency",
    "cover_ratio",
    "reference_price",
    "source",
    "source_url",
    "notes",
}


def read_auction_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing carbon auction input {path}. "
            "Run python src/seed_demo_data.py to create demo inputs, or add a curated official CSV."
        )
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Carbon auction input {path} is empty.")
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Carbon auction input {path} is missing required columns: {', '.join(sorted(missing))}")
    return frame


def load_auction_data() -> pd.DataFrame:
    frames = []
    for market, candidates in AUCTION_INPUTS.items():
        path = next((CARBON_RAW / filename for filename in candidates if (CARBON_RAW / filename).exists()), None)
        if path is None:
            raise FileNotFoundError(
                f"Missing {market} carbon auction input. Expected one of: {', '.join(candidates)}."
            )
        frame = read_auction_csv(path)
        frame["input_file"] = path.name
        frames.append(frame)

    auctions = pd.concat(frames, ignore_index=True)
    auctions["auction_date"] = pd.to_datetime(auctions["auction_date"], errors="coerce")
    for column in ["auction_volume", "clearing_price", "cover_ratio", "reference_price"]:
        auctions[column] = pd.to_numeric(auctions[column], errors="coerce")
    return auctions.sort_values(["auction_date", "market"]).reset_index(drop=True)
