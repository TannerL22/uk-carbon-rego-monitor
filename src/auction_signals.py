"""Calculate auction volume and demand (cover-ratio) signals.

The headline demand signal uses official EEX EU ETS1 auction results, which are
refreshed automatically. UKA auction demand is reported separately and labelled
by provenance, because the committed UKA auction CSV is an illustrative sample
until it is curated from ICE Report Centre.
"""

from __future__ import annotations

import json

import pandas as pd

from load_carbon_data import load_auction_data
from project_paths import ROOT


OUTPUT = ROOT / "data" / "processed" / "auction_signals.json"
TRAILING_AUCTIONS = 10
MIN_TRAILING_AUCTIONS = 3
COVER_RATIO_BAND = 0.15
SERIES_AUCTIONS = 60


def demand_signal(latest_cover: float | None, trailing_cover: float | None, market: str = "") -> str:
    prefix = f"Latest {market} auction demand".replace("  ", " ")
    if latest_cover is None or trailing_cover is None or pd.isna(latest_cover) or pd.isna(trailing_cover):
        return f"{market} auction demand data insufficient".strip()
    if latest_cover > trailing_cover + COVER_RATIO_BAND:
        return f"{prefix} stronger than recent average"
    if latest_cover < trailing_cover - COVER_RATIO_BAND:
        return f"{prefix} weaker than recent average"
    return f"{prefix}: neutral"


def market_demand(auctions: pd.DataFrame, market: str) -> dict[str, object]:
    rows = auctions[auctions["market"] == market].dropna(subset=["auction_date"]).sort_values("auction_date")
    if rows.empty:
        return {"available": False, "demand_signal": f"{market} auction data not loaded", "source": "", "series": []}

    covers = rows["cover_ratio"].dropna()
    latest_cover = float(covers.iloc[-1]) if not covers.empty else None
    # Trailing average excludes the latest auction so it is compared against history.
    history = covers.iloc[:-1].tail(TRAILING_AUCTIONS)
    trailing_cover = float(history.mean()) if len(history) >= MIN_TRAILING_AUCTIONS else None

    volumes = rows.groupby("auction_date")["auction_volume"].sum()
    latest_volume = float(volumes.iloc[-1])
    trailing_volume = float(volumes.iloc[:-1].tail(TRAILING_AUCTIONS).mean()) if len(volumes) > 1 else latest_volume
    volume_signal = (
        "Auction supply above recent average" if latest_volume > trailing_volume * 1.05
        else "Auction supply below recent average" if latest_volume < trailing_volume * 0.95
        else "Auction supply near recent average"
    )
    return {
        "available": True,
        "latest_auction_date": rows["auction_date"].iloc[-1].date().isoformat(),
        "latest_volume": int(latest_volume),
        "latest_cover_ratio": None if latest_cover is None else round(latest_cover, 2),
        "trailing_cover_ratio": None if trailing_cover is None else round(trailing_cover, 2),
        "demand_signal": demand_signal(latest_cover, trailing_cover, market),
        "volume_signal": volume_signal,
        "input_file": str(rows["input_file"].iloc[-1]) if "input_file" in rows else "",
        "source": str(rows["source"].iloc[-1]),
        "series": [
            {"date": date.date().isoformat(), "auction_volume": int(volume)}
            for date, volume in volumes.tail(SERIES_AUCTIONS).items()
        ],
    }


def main() -> None:
    auctions = load_auction_data()
    eua = market_demand(auctions, "EUA")
    uka = market_demand(auctions, "UKA")
    if not uka["available"]:
        uka["provenance"] = "Not loaded (pending ICE curation)"
    elif "illustrative" in str(uka.get("source", "")).lower():
        uka["provenance"] = "Illustrative sample (not ICE-verified)"
    else:
        uka["provenance"] = "Manually curated ICE input"

    output = {
        # Headline fields come from official EEX EUA auctions.
        "basis": "EEX EU ETS1 primary auctions (official)",
        "latest_auction_date": eua.get("latest_auction_date"),
        "latest_cover_ratio": eua.get("latest_cover_ratio"),
        "trailing_cover_ratio": eua.get("trailing_cover_ratio"),
        "demand_signal": eua["demand_signal"],
        "volume_signal": eua.get("volume_signal"),
        "series": eua["series"],
        "eua": eua,
        "uka": uka,
        "note": (
            f"Headline demand compares the latest EUA cover ratio with the previous {TRAILING_AUCTIONS} auctions "
            f"(+/-{COVER_RATIO_BAND} band). UKA auction demand is shown separately; provenance: {uka['provenance']}."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Auction signal: {eua['demand_signal']}. UKA ({uka['provenance']}): {uka['demand_signal']}.")


if __name__ == "__main__":
    main()
