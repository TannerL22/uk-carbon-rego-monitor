"""Fetch live NESO Carbon Intensity API data for the power module."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_POWER = ROOT / "data" / "raw" / "power"
SOURCE_REGISTER = ROOT / "data" / "source_register.csv"
NORMALIZED_CSV = RAW_POWER / "neso_generation_mix_live.csv"
RAW_JSON = RAW_POWER / "neso_carbon_intensity_api_raw.json"
METADATA_JSON = RAW_POWER / "neso_fetch_metadata.json"

BASE_URL = "https://api.carbonintensity.org.uk"
FETCH_DAYS = 7
TIMEOUT_SECONDS = 30
FUELS = ["gas", "wind", "solar", "nuclear", "biomass", "hydro", "imports", "coal", "other"]


class NesoFetchError(RuntimeError):
    """Raised when the live NESO fetch cannot produce usable dashboard data."""


def iso_z(value: datetime) -> str:
    return value.replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%MZ")


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "uk-carbon-rego-monitor/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise NesoFetchError(f"NESO API request failed for {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise NesoFetchError(f"NESO API returned non-JSON response for {url}.") from exc

    if not isinstance(payload, dict) or "data" not in payload:
        raise NesoFetchError(f"NESO API response did not include a data array for {url}.")
    return payload


def intensity_lookup(payload: dict[str, Any]) -> dict[str, float]:
    lookup: dict[str, float] = {}
    for record in payload.get("data", []):
        if not isinstance(record, dict):
            continue
        key = str(record.get("from", ""))
        intensity = record.get("intensity", {})
        if not isinstance(intensity, dict):
            continue
        value = intensity.get("actual")
        if value is None:
            value = intensity.get("forecast")
        if key and value is not None:
            lookup[key] = float(value)
    return lookup


def normalize_generation(payload: dict[str, Any], intensities: dict[str, float]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in payload.get("data", []):
        if not isinstance(record, dict):
            continue
        timestamp = str(record.get("from", ""))
        generation_mix = record.get("generationmix", [])
        if not timestamp or not isinstance(generation_mix, list) or timestamp not in intensities:
            continue

        shares = {fuel: 0.0 for fuel in FUELS}
        for item in generation_mix:
            if not isinstance(item, dict):
                continue
            fuel = str(item.get("fuel", "")).lower()
            percentage = item.get("perc")
            if percentage is None:
                continue
            if fuel in shares:
                shares[fuel] = float(percentage)
            else:
                shares["other"] += float(percentage)

        rows.append(
            {
                "datetime": timestamp,
                "carbon_intensity_gco2_kwh": round(float(intensities[timestamp]), 1),
                "gas_share": round(shares["gas"], 1),
                "wind_share": round(shares["wind"], 1),
                "solar_share": round(shares["solar"], 1),
                "nuclear_share": round(shares["nuclear"], 1),
                "biomass_share": round(shares["biomass"], 1),
                "hydro_share": round(shares["hydro"], 1),
                "imports_share": round(shares["imports"], 1),
                "coal_share": round(shares["coal"], 1),
                "other_share": round(shares["other"], 1),
            }
        )

    if not rows:
        raise NesoFetchError("NESO API returned no overlapping intensity and generation mix records.")
    rows.sort(key=lambda row: str(row["datetime"]))
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def update_source_register(metadata: dict[str, str]) -> None:
    if not SOURCE_REGISTER.exists():
        return

    with SOURCE_REGISTER.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    for row in rows:
        if row.get("source_id") == "SRC-005":
            row["downloaded_at"] = metadata["fetched_at"]
            row["published_at"] = metadata["to"]
            row["data_period_start"] = metadata["from"]
            row["data_period_end"] = metadata["to"]
            row["source_url"] = BASE_URL
            row["manual_or_api"] = "api"
            row["known_limitations"] = "Live public API fetch at build time; values may be revised by NESO."

    with SOURCE_REGISTER.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=FETCH_DAYS)
    from_param = iso_z(start)
    to_param = iso_z(now)

    intensity_url = f"{BASE_URL}/intensity/{from_param}/{to_param}"
    generation_url = f"{BASE_URL}/generation/{from_param}/{to_param}"

    intensity_payload = fetch_json(intensity_url)
    generation_payload = fetch_json(generation_url)
    rows = normalize_generation(generation_payload, intensity_lookup(intensity_payload))

    fetched_at = iso_z(datetime.now(UTC))
    metadata = {
        "fetched_at": fetched_at,
        "from": rows[0]["datetime"],
        "to": rows[-1]["datetime"],
        "intensity_url": intensity_url,
        "generation_url": generation_url,
        "record_count": str(len(rows)),
    }

    write_csv(NORMALIZED_CSV, rows)
    RAW_JSON.write_text(
        json.dumps({"intensity": intensity_payload, "generation": generation_payload}, indent=2),
        encoding="utf-8",
    )
    METADATA_JSON.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    update_source_register(metadata)

    print(f"Fetched {len(rows)} NESO power records from {metadata['from']} to {metadata['to']}.")


if __name__ == "__main__":
    main()
