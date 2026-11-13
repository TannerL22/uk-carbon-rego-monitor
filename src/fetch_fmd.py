"""Fetch the current GOV.UK Fuel Mix Disclosure (FMD) data table.

GOV.UK publishes one FMD table per disclosure period (1 April - 31 March),
usually each summer, and replaces the page content when the next period is
published. This script parses the current table into
``data/raw/fmd/fmd_<start>_<end>.csv``. Earlier periods' files are kept, so
contracts can still be matched to the table for their own disclosure period.
"""

from __future__ import annotations

import csv
import html
import re
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fetch_uk_ets_ccm import GovUkTableParser
from project_paths import ROOT
from source_register import upsert_source


FMD_RAW = ROOT / "data" / "raw" / "fmd"
SOURCE_URL = "https://www.gov.uk/government/publications/fuel-mix-disclosure-data-table/fuel-mix-disclosure-data-table"
SOURCE_ID = "SRC-009"
TIMEOUT_SECONDS = 30
FUEL_TYPES = ["Coal", "Natural Gas", "Nuclear", "Renewables", "Other"]

OUTPUT_COLUMNS = [
    "disclosure_period",
    "fuel_type",
    "uk_average_mix_pct",
    "residual_mix_pct",
    "emissions_factor_gco2_per_kwh",
    "uk_generation_average_factor_gco2_per_kwh",
    "radioactive_waste_g_per_kwh",
    "source_url",
    "source_date",
    "notes",
]


class FmdFetchError(RuntimeError):
    """Raised when the GOV.UK FMD table cannot be fetched or parsed."""


def fetch_html() -> str:
    request = Request(SOURCE_URL, headers={"User-Agent": "uk-carbon-rego-monitor/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise FmdFetchError(f"GOV.UK FMD table request failed for {SOURCE_URL}: {exc}") from exc


def page_text(page: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))


def normalise_fuel(label: str) -> str:
    name = re.sub(r"\(.*?\)", "", label).strip().lower()
    if name.startswith("other"):
        return "Other"
    for fuel in FUEL_TYPES:
        if name == fuel.lower():
            return fuel
    return ""


def parse_number(value: str) -> float | None:
    cleaned = value.strip().replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_disclosure_period(text: str) -> tuple[str, str, str]:
    match = re.search(r"disclosure period\s+(\d{1,2} \w+ \d{4}) to (\d{1,2} \w+ \d{4})", text, flags=re.I)
    if not match:
        raise FmdFetchError("GOV.UK FMD page did not state the disclosure period.")
    start = datetime.strptime(match.group(1), "%d %B %Y").date()
    end = datetime.strptime(match.group(2), "%d %B %Y").date()
    return f"{start.year}-{str(end.year)[2:]}", start.isoformat(), end.isoformat()


def parse_published_at(text: str) -> str:
    match = re.search(r"Updated\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", text)
    if not match:
        return ""
    try:
        return datetime.strptime(match.group(1), "%d %B %Y").date().isoformat()
    except ValueError:
        return ""


def mix_table(table: list[list[str]]) -> dict[str, float]:
    mix = {}
    for row in table[1:]:
        fuel = normalise_fuel(row[0]) if row else ""
        value = parse_number(row[1]) if len(row) > 1 else None
        if fuel and value is not None:
            mix[fuel] = value
    return mix


def parse_fmd(page: str) -> dict[str, object]:
    text = page_text(page)
    period, period_start, period_end = parse_disclosure_period(text)

    parser = GovUkTableParser()
    parser.feed(page)
    percentage_tables = [t for t in parser.tables if len(t[0]) >= 2 and t[0][1].strip() == "%"]
    factor_tables = [t for t in parser.tables if any("g/kwh" in cell.lower() for cell in t[0])]
    # Page order: section 2 residual fuel mix, section 3 emissions factors, section 4 UK fuel mix.
    if len(percentage_tables) != 2 or len(factor_tables) != 1:
        raise FmdFetchError(
            f"Unexpected GOV.UK FMD table layout: {len(percentage_tables)} percentage and {len(factor_tables)} factor tables."
        )
    residual = mix_table(percentage_tables[0])
    uk_mix = mix_table(percentage_tables[1])

    factors: dict[str, float] = {}
    overall_average = None
    for row in factor_tables[0][1:]:
        # Use the latest year's factor; GOV.UK notes say to use the prior year where the latest is "-".
        value = next((number for number in (parse_number(cell) for cell in row[1:]) if number is not None), None)
        if row and row[0].strip().lower().startswith("overall average"):
            overall_average = value
        elif normalise_fuel(row[0]) and value is not None:
            factors[normalise_fuel(row[0])] = value

    missing = [fuel for fuel in FUEL_TYPES if fuel not in residual or fuel not in uk_mix or fuel not in factors]
    if missing or overall_average is None:
        raise FmdFetchError(f"GOV.UK FMD table is missing values for: {', '.join(missing) or 'overall average'}.")
    for name, mix in (("residual", residual), ("UK", uk_mix)):
        if abs(sum(mix.values()) - 100) > 1.0:
            raise FmdFetchError(f"GOV.UK FMD {name} mix sums to {sum(mix.values()):.1f}%, expected ~100%.")

    waste_match = re.search(r"radioactive waste\s+([0-9.]+)\s*g/kWh", text, flags=re.I)
    return {
        "disclosure_period": period,
        "period_start": period_start,
        "period_end": period_end,
        "published_at": parse_published_at(text),
        "residual": residual,
        "uk_mix": uk_mix,
        "factors": factors,
        "overall_average": overall_average,
        "radioactive_waste": float(waste_match.group(1)) if waste_match else "",
    }


def output_path(period_start: str, period_end: str) -> Path:
    return FMD_RAW / f"fmd_{period_start[:4]}_{period_end[:4]}.csv"


def write_table(table: dict[str, object]) -> Path:
    path = output_path(str(table["period_start"]), str(table["period_end"]))
    note = (
        f"Official GOV.UK Fuel Mix Disclosure table for {table['period_start']} to {table['period_end']}; "
        "parsed by src/fetch_fmd.py."
    )
    rows = [
        {
            "disclosure_period": table["disclosure_period"],
            "fuel_type": fuel,
            "uk_average_mix_pct": table["uk_mix"][fuel],
            "residual_mix_pct": table["residual"][fuel],
            "emissions_factor_gco2_per_kwh": table["factors"][fuel],
            "uk_generation_average_factor_gco2_per_kwh": table["overall_average"],
            "radioactive_waste_g_per_kwh": table["radioactive_waste"],
            "source_url": SOURCE_URL,
            "source_date": table["published_at"],
            "notes": note,
        }
        for fuel in FUEL_TYPES
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temp_path = Path(handle.name)
    temp_path.replace(path)
    return path


def main() -> None:
    downloaded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    table = parse_fmd(fetch_html())
    path = write_table(table)
    upsert_source(
        {
            "source_id": SOURCE_ID,
            "dataset_name": f"GOV.UK Fuel Mix Disclosure data table {table['disclosure_period']}",
            "source_owner": "Department for Energy Security and Net Zero",
            "source_type": "official public disclosure table",
            "source_url": SOURCE_URL,
            "manual_or_api": "public file",
            "downloaded_at": downloaded_at,
            "published_at": table["published_at"],
            "data_period_start": table["period_start"],
            "data_period_end": table["period_end"],
            "used_for": "Latest FMD factors for carbon-cost and emissions-reporting context",
            "known_limitations": "Official GOV.UK FMD table for reporting context only; not an official customer Scope 2 calculation.",
        }
    )
    print(f"Fetched GOV.UK FMD table for {table['disclosure_period']} -> {path.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
