"""Validate the manually curated ICE UKA auction input file.

The UKA auction CSV is intentionally manual for this MVP. ICE is the official
auction platform, but the build does not scrape ICE. This validator makes the
manual input explicit and fails fast if the file is missing, empty, or malformed.

The committed file currently holds illustrative values (they diverge from the
official GOV.UK monthly averages; see source control SC-008). The source-register
label is derived from the CSV's own ``source``/``manual_update_note`` text, so it
switches to "ICE UKA auction results" once real curated rows replace it.
"""

from __future__ import annotations

import pandas as pd

from project_paths import ROOT
from source_register import upsert_source


INPUT = ROOT / "data" / "raw" / "carbon" / "uka_auction_results.csv"
SOURCE_ID = "SRC-003"

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
    "downloaded_at",
    "manual_update_note",
    "notes",
}


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            "Missing data/raw/carbon/uka_auction_results.csv. "
            "Add the manually curated ICE UKA auction CSV before running the dashboard build."
        )

    data = pd.read_csv(INPUT, dtype=str).fillna("")
    if data.empty:
        raise ValueError("data/raw/carbon/uka_auction_results.csv is empty.")

    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(f"UKA auction CSV is missing required columns: {', '.join(sorted(missing))}")

    if set(data["market"].str.upper()) != {"UKA"}:
        raise ValueError("UKA auction CSV must contain only market=UKA rows.")
    if set(data["currency"].str.upper()) != {"GBP"}:
        raise ValueError("UKA auction CSV must contain only currency=GBP rows.")

    parsed_dates = pd.to_datetime(data["auction_date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("UKA auction CSV contains unparseable auction_date values.")
    if parsed_dates.duplicated().any():
        duplicates = parsed_dates[parsed_dates.duplicated()].dt.date.astype(str).tolist()
        raise ValueError(f"UKA auction CSV contains duplicate auction_date values: {', '.join(duplicates)}")

    for column in ["auction_volume", "clearing_price", "cover_ratio", "reference_price"]:
        numeric = pd.to_numeric(data[column], errors="coerce")
        if numeric.isna().any():
            raise ValueError(f"UKA auction CSV contains non-numeric values in {column}.")
        if (numeric <= 0).any():
            raise ValueError(f"UKA auction CSV contains non-positive values in {column}.")

    if data["source_url"].str.strip().eq("").any():
        raise ValueError("UKA auction CSV requires source_url on every row.")
    if data["downloaded_at"].str.strip().eq("").any():
        raise ValueError("UKA auction CSV requires downloaded_at/manual update date on every row.")
    if data["manual_update_note"].str.strip().eq("").any():
        raise ValueError("UKA auction CSV requires manual_update_note on every row.")

    update_source_register(data, parsed_dates)
    label = "illustrative (not ICE-verified)" if is_illustrative(data) else "manually curated"
    print(f"Validated {len(data)} {label} UKA auction rows from {parsed_dates.min().date()} to {parsed_dates.max().date()}.")


def is_illustrative(data: pd.DataFrame) -> bool:
    """True when any row's provenance text marks it as an illustrative/sample value."""

    provenance = (data["source"] + " " + data["manual_update_note"]).str.lower()
    return bool(provenance.str.contains("illustrative|sample|not verified", regex=True).any())


def update_source_register(data: pd.DataFrame, parsed_dates: pd.Series) -> None:
    update_date = str(data["downloaded_at"].dropna().astype(str).max())
    illustrative = is_illustrative(data)
    upsert_source(
        {
            "source_id": SOURCE_ID,
            "dataset_name": "UKA auction results (illustrative sample)" if illustrative else "ICE UKA auction results",
            "source_owner": "Project illustrative sample" if illustrative else "ICE Futures Europe",
            "source_type": "illustrative sample / pending ICE curation" if illustrative else "official source / manually curated CSV",
            "source_url": str(data["source_url"].iloc[0]),
            "manual_or_api": "manual",
            "downloaded_at": update_date,
            "published_at": update_date,
            "data_period_start": parsed_dates.min().date().isoformat(),
            "data_period_end": parsed_dates.max().date().isoformat(),
            "used_for": "UKA auction demand (cover ratio) context only; UKA price signals use GOV.UK monthly averages",
            "known_limitations": (
                "Illustrative UKA auction values, not verified against ICE Report Centre; cross-checked against official "
                "GOV.UK monthly averages by source control SC-008. Replace with curated ICE results before analytical use."
                if illustrative
                else "Manually curated CSV from ICE UKA auction result references; not automatically scraped and not a live secondary-market feed."
            ),
        }
    )


if __name__ == "__main__":
    main()
