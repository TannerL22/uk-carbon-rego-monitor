"""Fetch monthly EUR/GBP reference rates from the ECB Data Portal.

Series ``EXR.M.GBP.EUR.SP00.A`` is the monthly average of the ECB's daily euro
foreign exchange reference rates, expressed as GBP per 1 EUR. It replaces the
static EUR/GBP assumption when converting EUA prices to GBP; the static rate in
``fx_assumptions.csv`` remains only as a fallback for months not yet published.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from project_paths import ROOT
from source_register import upsert_source


OUTPUT = ROOT / "data" / "raw" / "carbon" / "ecb_eurgbp_monthly.csv"
SERIES_KEY = "EXR/M.GBP.EUR.SP00.A"
API_URL = "https://data-api.ecb.europa.eu/service/data"
SERIES_PAGE = "https://data.ecb.europa.eu/data/datasets/EXR/EXR.M.GBP.EUR.SP00.A"
SOURCE_ID = "SRC-011"
YEARS_OF_HISTORY = 3
TIMEOUT_SECONDS = 30
OUTPUT_COLUMNS = ["month", "eur_gbp", "source", "source_url", "downloaded_at"]


class EcbFetchError(RuntimeError):
    """Raised when ECB reference rates cannot be fetched or parsed."""


def request_url(start_month: str) -> str:
    return f"{API_URL}/{SERIES_KEY}?format=csvdata&startPeriod={start_month}"


def fetch_csv(url: str) -> str:
    request = Request(url, headers={"Accept": "text/csv", "User-Agent": "uk-carbon-rego-monitor/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise EcbFetchError(f"ECB data API request failed for {url}: {exc}") from exc


def parse_rates(payload: str) -> list[tuple[str, float]]:
    rates: list[tuple[str, float]] = []
    for row in csv.DictReader(io.StringIO(payload)):
        if row.get("CURRENCY") != "GBP" or row.get("CURRENCY_DENOM") != "EUR":
            continue
        try:
            value = float(row["OBS_VALUE"])
        except (KeyError, TypeError, ValueError):
            continue
        if not 0.5 < value < 1.5:
            raise EcbFetchError(f"Implausible EUR/GBP rate {value} for {row.get('TIME_PERIOD')}.")
        rates.append((str(row["TIME_PERIOD"]), value))
    if not rates:
        raise EcbFetchError("ECB data API returned no EUR/GBP observations.")
    return sorted(rates)


def write_rates(rates: list[tuple[str, float]], url: str, downloaded_at: str) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=OUTPUT.parent, suffix=".tmp") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for month, value in rates:
            writer.writerow(
                {
                    "month": month,
                    "eur_gbp": round(value, 6),
                    "source": "ECB euro foreign exchange reference rates (monthly average)",
                    "source_url": url,
                    "downloaded_at": downloaded_at,
                }
            )
        temp_path = Path(handle.name)
    temp_path.replace(OUTPUT)


def main() -> None:
    now = datetime.now(UTC)
    url = request_url(f"{now.year - YEARS_OF_HISTORY}-01")
    rates = parse_rates(fetch_csv(url))
    downloaded_at = now.strftime("%Y-%m-%dT%H:%MZ")
    write_rates(rates, url, downloaded_at)
    upsert_source(
        {
            "source_id": SOURCE_ID,
            "dataset_name": "ECB EUR/GBP monthly reference rate",
            "source_owner": "European Central Bank",
            "source_type": "official public statistics API",
            "source_url": SERIES_PAGE,
            "manual_or_api": "api",
            "downloaded_at": downloaded_at,
            "published_at": rates[-1][0],
            "data_period_start": rates[0][0],
            "data_period_end": rates[-1][0],
            "used_for": "EUA EUR to GBP conversion for the monthly UKA-EUA spread",
            "known_limitations": "Monthly average of ECB daily reference rates (indicative, for information purposes); not a traded FX rate.",
        }
    )
    print(f"Fetched {len(rates)} ECB EUR/GBP monthly rates from {rates[0][0]} to {rates[-1][0]} (latest {rates[-1][1]:.4f}).")


if __name__ == "__main__":
    main()
