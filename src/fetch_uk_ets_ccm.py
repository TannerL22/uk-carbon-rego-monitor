"""Fetch GOV.UK UK ETS CCM trigger and monthly average price tables.

The GOV.UK page publishes official Cost Containment Mechanism trigger prices
and monthly average futures prices. These values are policy/market context, not
auction clearing prices and not a live trading feed.
"""

from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CARBON_RAW = ROOT / "data" / "raw" / "carbon"
SOURCE_REGISTER = ROOT / "data" / "source_register.csv"
OUTPUT = CARBON_RAW / "uk_ets_ccm_monthly_prices.csv"

SOURCE_URL = (
    "https://www.gov.uk/government/publications/taking-part-in-the-uk-emissions-trading-scheme-markets/"
    "cost-containment-mechanism-ccm-trigger-prices-and-average-monthly-prices-full-table"
)
TIMEOUT_SECONDS = 30
SOURCE_ID = "SRC-007"

OUTPUT_COLUMNS = [
    "month",
    "monitoring_window_months",
    "reference_period",
    "monitoring_period",
    "monthly_average_price",
    "trigger_price",
    "ccm_triggered",
    "contract_reference",
    "currency",
    "source",
    "source_url",
    "downloaded_at",
    "published_at",
    "notes",
]


class UkEtsCcmFetchError(RuntimeError):
    """Raised when the GOV.UK CCM table cannot be fetched or parsed."""


class GovUkTableParser(HTMLParser):
    """Small dependency-free table parser for GOV.UK publication pages."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._table: list[list[str]] = []
        self._in_row = False
        self._row: list[str] = []
        self._in_cell = False
        self._cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._row:
                self._table.append(self._row)
            self._in_row = False
        elif tag == "table" and self._in_table:
            if self._table:
                self.tables.append(self._table)
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)


def iso_z(value: datetime) -> str:
    return value.replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%MZ")


def fetch_html() -> str:
    request = Request(SOURCE_URL, headers={"User-Agent": "uk-carbon-rego-monitor/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise UkEtsCcmFetchError(f"GOV.UK CCM table request failed for {SOURCE_URL}: {exc}") from exc


def parse_money(value: str) -> float | str:
    cleaned = value.strip().replace(",", "").replace("£", "").replace("Ł", "")
    if not cleaned or cleaned.upper() == "TBD":
        return ""
    return round(float(cleaned), 2)


def parse_month(value: str) -> str:
    try:
        return datetime.strptime(value.strip(), "%b-%y").strftime("%Y-%m")
    except ValueError as exc:
        raise UkEtsCcmFetchError(f"Could not parse CCM month value '{value}'.") from exc


def parse_published_at(html: str) -> str:
    match = re.search(r"Updated\s+([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})", html)
    if not match:
        return ""
    try:
        return datetime.strptime(match.group(1), "%d %B %Y").date().isoformat()
    except ValueError:
        return ""


def parse_tables(html: str, downloaded_at: str, published_at: str) -> list[dict[str, object]]:
    parser = GovUkTableParser()
    parser.feed(html)
    if not parser.tables:
        raise UkEtsCcmFetchError("GOV.UK CCM page did not include any parseable tables.")

    rows: list[dict[str, object]] = []
    for table in parser.tables:
        header = [cell.lower() for cell in table[0]]
        if "month" not in header or "trigger price" not in header:
            continue

        month_idx = header.index("month")
        reference_idx = header.index("2-year reference period")
        trigger_idx = header.index("trigger price")
        triggered_idx = next((idx for idx, value in enumerate(header) if "triggered" in value), None)
        monitoring_idx = next((idx for idx, value in enumerate(header) if "monitoring period" in value), None)
        average_indices = [idx for idx, value in enumerate(header) if "average price" in value]
        if triggered_idx is None or monitoring_idx is None or not average_indices:
            continue

        monitoring_window_months = len(average_indices)
        latest_average_idx = average_indices[-1]
        for source_row in table[1:]:
            if len(source_row) <= max(triggered_idx, latest_average_idx, monitoring_idx, reference_idx):
                continue
            monthly_average = parse_money(source_row[latest_average_idx])
            rows.append(
                {
                    "month": parse_month(source_row[month_idx]),
                    "monitoring_window_months": monitoring_window_months,
                    "reference_period": source_row[reference_idx],
                    "monitoring_period": source_row[monitoring_idx],
                    "monthly_average_price": monthly_average,
                    "trigger_price": parse_money(source_row[trigger_idx]),
                    "ccm_triggered": source_row[triggered_idx],
                    "contract_reference": "",
                    "currency": "GBP",
                    "source": "GOV.UK UK ETS Cost Containment Mechanism table",
                    "source_url": SOURCE_URL,
                    "downloaded_at": downloaded_at,
                    "published_at": published_at,
                    "notes": (
                        "Official GOV.UK CCM table. Monthly average price is the final monthly average in "
                        f"the {monitoring_window_months}-month monitoring period; blank values indicate GOV.UK TBD rows."
                    ),
                }
            )

    if not rows:
        raise UkEtsCcmFetchError("GOV.UK CCM page tables did not yield any CCM price rows.")
    rows.sort(key=lambda row: str(row["month"]))
    return rows


def write_csv_atomically(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def update_source_register(rows: list[dict[str, object]], downloaded_at: str, published_at: str) -> None:
    if not SOURCE_REGISTER.exists():
        return

    with SOURCE_REGISTER.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        register_rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not fieldnames:
        return

    source_row = {
        "source_id": SOURCE_ID,
        "dataset_name": "GOV.UK UK ETS CCM monthly prices",
        "source_owner": "Department for Energy Security and Net Zero / UK ETS Authority",
        "source_type": "official public policy table",
        "source_url": SOURCE_URL,
        "manual_or_api": "public file",
        "downloaded_at": downloaded_at,
        "published_at": published_at or str(rows[-1]["month"]),
        "data_period_start": str(rows[0]["month"]),
        "data_period_end": str(rows[-1]["month"]),
        "used_for": "UKA monthly futures-average and CCM context",
        "known_limitations": "Official GOV.UK CCM table; monthly average futures price context, not auction clearing price and not a live trading feed.",
    }

    replaced = False
    for index, row in enumerate(register_rows):
        if row.get("source_id") == SOURCE_ID:
            register_rows[index] = source_row
            replaced = True
            break
    if not replaced:
        register_rows.append(source_row)

    with SOURCE_REGISTER.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(register_rows)


def main() -> None:
    downloaded_at = iso_z(datetime.now(UTC))
    html = fetch_html()
    published_at = parse_published_at(html)
    rows = parse_tables(html, downloaded_at, published_at)
    write_csv_atomically(OUTPUT, rows)
    update_source_register(rows, downloaded_at, published_at)
    completed = [row for row in rows if row["monthly_average_price"] != ""]
    latest = completed[-1] if completed else rows[-1]
    print(
        "Fetched GOV.UK UK ETS CCM table: "
        f"{len(rows)} rows from {rows[0]['month']} to {rows[-1]['month']}; "
        f"latest completed average {latest['month']}."
    )


if __name__ == "__main__":
    main()
