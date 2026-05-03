"""Optionally fetch a third-party EU carbon market reference.

This module is intentionally optional. GitHub Pages visitors never call
Trading Economics directly, and the build does not require an API key. If
TRADING_ECONOMICS_API_KEY is absent, the script writes a disabled status JSON
so the dashboard can clearly state that no third-party reference is loaded.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_OUTPUT = ROOT / "data" / "raw" / "carbon" / "trading_economics_eu_carbon_reference.csv"
PROCESSED_OUTPUT = ROOT / "data" / "processed" / "carbon_market_reference.json"
SOURCE_REGISTER = ROOT / "data" / "source_register.csv"

SYMBOL = os.getenv("TRADING_ECONOMICS_CARBON_SYMBOL", "EECXM:IND")
SOURCE_URL = "https://tradingeconomics.com/commodity/carbon"
DOCS_URL = "https://docs.tradingeconomics.com/markets/historical/"
SNAPSHOT_DOCS_URL = "https://docs.tradingeconomics.com/markets/snapshot/"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def disabled_payload(reason: str) -> dict[str, object]:
    return {
        "available": False,
        "enabled": False,
        "provider": "Trading Economics",
        "label": "Third-party market reference",
        "symbol": SYMBOL,
        "source_url": SOURCE_URL,
        "docs_url": DOCS_URL,
        "downloaded_at": utc_now(),
        "note": reason,
        "limitation": (
            "Optional third-party market reference only. It is separate from official EEX auction, "
            "ICE UKA auction, and GOV.UK CCM inputs and is not required for the dashboard."
        ),
        "series": [],
    }


def write_processed(payload: dict[str, object]) -> None:
    PROCESSED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def request_json(url: str, api_key: str) -> list[dict[str, object]]:
    separator = "&" if "?" in url else "?"
    full_url = f"{url}{separator}{urlencode({'c': api_key, 'f': 'json'})}"
    request = Request(full_url, headers={"User-Agent": "uk-carbon-rego-monitor/1.0"})
    with urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict):
        return [payload]
    if not isinstance(payload, list):
        raise ValueError("Trading Economics API returned an unexpected response shape.")
    return payload


def parse_number(value: object) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value: object) -> str:
    if value in ("", None):
        return ""
    text = str(value)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text[:10]


def normalise_history(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    normalised: list[dict[str, object]] = []
    for row in rows:
        close = parse_number(row.get("Close"))
        if close is None:
            continue
        normalised.append(
            {
                "symbol": str(row.get("Symbol", SYMBOL)),
                "date": parse_date(row.get("Date")),
                "open": parse_number(row.get("Open")),
                "high": parse_number(row.get("High")),
                "low": parse_number(row.get("Low")),
                "close": close,
                "currency": "EUR",
                "source": "Trading Economics API",
                "source_url": SOURCE_URL,
            }
        )
    return sorted(normalised, key=lambda item: str(item["date"]))


def write_raw_csv(rows: list[dict[str, object]]) -> None:
    RAW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["symbol", "date", "open", "high", "low", "close", "currency", "source", "source_url"]
    with RAW_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_source_register(start_date: str, end_date: str, downloaded_at: str) -> None:
    fieldnames = [
        "source_id",
        "dataset_name",
        "source_owner",
        "source_type",
        "source_url",
        "manual_or_api",
        "downloaded_at",
        "published_at",
        "data_period_start",
        "data_period_end",
        "used_for",
        "known_limitations",
    ]
    rows: list[dict[str, str]] = []
    if SOURCE_REGISTER.exists():
        with SOURCE_REGISTER.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

    source_row = {
        "source_id": "SRC-008",
        "dataset_name": "Trading Economics EU Carbon Permits reference",
        "source_owner": "Trading Economics",
        "source_type": "third-party market reference",
        "source_url": SOURCE_URL,
        "manual_or_api": "api",
        "downloaded_at": downloaded_at,
        "published_at": downloaded_at,
        "data_period_start": start_date,
        "data_period_end": end_date,
        "used_for": "Optional EU carbon third-party market reference",
        "known_limitations": (
            "Third-party market reference fetched with API secret during build; not an official exchange feed, "
            "not a licensed live trading terminal, and separate from official auction/CCM inputs."
        ),
    }
    rows = [row for row in rows if row.get("source_id") != "SRC-008"]
    rows.append(source_row)
    with SOURCE_REGISTER.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_payload(rows: list[dict[str, object]], downloaded_at: str) -> dict[str, object]:
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else None
    latest_close = float(latest["close"])
    previous_close = float(previous["close"]) if previous else None
    daily_change = None if previous_close is None else round(latest_close - previous_close, 2)
    daily_change_pct = None if previous_close in (None, 0.0) else round((latest_close - previous_close) / previous_close * 100, 2)
    return {
        "available": True,
        "enabled": True,
        "provider": "Trading Economics",
        "label": "Third-party market reference",
        "symbol": SYMBOL,
        "instrument": "EU Carbon Permits",
        "source_url": SOURCE_URL,
        "docs_url": DOCS_URL,
        "snapshot_docs_url": SNAPSHOT_DOCS_URL,
        "downloaded_at": downloaded_at,
        "data_period_start": rows[0]["date"],
        "data_period_end": latest["date"],
        "latest_date": latest["date"],
        "latest_price_eur": round(latest_close, 2),
        "daily_change_eur": daily_change,
        "daily_change_pct": daily_change_pct,
        "unit": "EUR",
        "note": "Third-party EU Carbon Permits market reference fetched at build time from Trading Economics.",
        "limitation": (
            "This is a third-party market reference, not an official exchange feed and not a substitute "
            "for the dashboard's official auction and GOV.UK policy-context data."
        ),
        "series": rows[-60:],
    }


def main() -> None:
    api_key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    if not api_key:
        write_processed(disabled_payload("Trading Economics API key not configured; optional market reference disabled."))
        print("Trading Economics reference skipped: TRADING_ECONOMICS_API_KEY is not configured.")
        return

    end = datetime.now(UTC).date()
    start = end - timedelta(days=120)
    endpoint = (
        f"https://api.tradingeconomics.com/markets/historical/{quote(SYMBOL, safe='')}"
        f"?{urlencode({'d1': start.isoformat(), 'd2': end.isoformat()})}"
    )
    downloaded_at = utc_now()
    try:
        raw_rows = request_json(endpoint, api_key)
        rows = normalise_history(raw_rows)
        if len(rows) < 2:
            raise ValueError("Trading Economics API returned fewer than two usable EU carbon observations.")
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        write_processed(disabled_payload(f"Trading Economics fetch failed during build: {exc}"))
        print(f"Trading Economics reference disabled after fetch failure: {exc}")
        return

    write_raw_csv(rows)
    update_source_register(str(rows[0]["date"]), str(rows[-1]["date"]), downloaded_at)
    write_processed(build_payload(rows, downloaded_at))
    print(f"Trading Economics EU carbon reference written for {rows[-1]['date']}.")


if __name__ == "__main__":
    main()
