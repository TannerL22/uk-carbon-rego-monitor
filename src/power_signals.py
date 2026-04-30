"""Calculate GB power-system fundamentals signals."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "power" / "neso_generation_mix_sample.csv"
LIVE_INPUT = ROOT / "data" / "raw" / "power" / "neso_generation_mix_live.csv"
METADATA_INPUT = ROOT / "data" / "raw" / "power" / "neso_fetch_metadata.json"
OUTPUT = ROOT / "data" / "processed" / "power_signals.json"


def main() -> None:
    input_path = LIVE_INPUT if LIVE_INPUT.exists() else INPUT
    if input_path == INPUT:
        raise FileNotFoundError("Live NESO power data is missing. Run python src/fetch_neso.py before power_signals.py.")

    power = pd.read_csv(input_path)
    if power.empty:
        raise ValueError("Live NESO power data is empty.")
    power["datetime"] = pd.to_datetime(power["datetime"], errors="coerce")
    numeric_columns = [column for column in power.columns if column != "datetime"]
    for column in numeric_columns:
        power[column] = pd.to_numeric(power[column], errors="coerce")
    power = power.sort_values("datetime")

    latest = power.iloc[-1]
    metadata = json.loads(METADATA_INPUT.read_text(encoding="utf-8")) if METADATA_INPUT.exists() else {}
    avg_ci = float(power["carbon_intensity_gco2_kwh"].mean())
    latest_ci = float(latest["carbon_intensity_gco2_kwh"])
    threshold = 10.0
    if latest_ci > avg_ci + threshold:
        carbon_signal = "Carbon intensity above recent average"
    elif latest_ci < avg_ci - threshold:
        carbon_signal = "Carbon intensity below recent average"
    else:
        carbon_signal = "Carbon intensity near recent average"

    latest_gas = float(latest["gas_share"])
    avg_gas = float(power["gas_share"].mean())
    latest_renewables = float(latest["wind_share"] + latest["solar_share"] + latest["hydro_share"])
    avg_renewables = float((power["wind_share"] + power["solar_share"] + power["hydro_share"]).mean())
    low_carbon_share = float(latest["wind_share"] + latest["solar_share"] + latest["hydro_share"] + latest["nuclear_share"] + latest["biomass_share"])

    if latest_gas > avg_gas + 2:
        driver = "higher gas share"
    elif latest_renewables < avg_renewables - 2:
        driver = "lower renewable output"
    else:
        driver = "mixed generation effects"

    output = {
        "latest_datetime": latest["datetime"].date().isoformat(),
        "latest_carbon_intensity_gco2_kwh": round(latest_ci, 1),
        "average_recent_carbon_intensity_gco2_kwh": round(avg_ci, 1),
        "average_30d_carbon_intensity_gco2_kwh": round(avg_ci, 1),
        "carbon_signal": carbon_signal,
        "gas_share": round(latest_gas, 1),
        "wind_solar_share": round(float(latest["wind_share"] + latest["solar_share"]), 1),
        "renewables_share": round(latest_renewables, 1),
        "low_carbon_share": round(low_carbon_share, 1),
        "main_driver": driver,
        "source": {
            "name": "NESO Carbon Intensity API",
            "fetched_at": metadata.get("fetched_at"),
            "data_period_start": metadata.get("from"),
            "data_period_end": metadata.get("to"),
            "intensity_url": metadata.get("intensity_url"),
            "generation_url": metadata.get("generation_url"),
            "record_count": metadata.get("record_count"),
        },
        "commentary": "Carbon intensity reflects the physical emissions profile of the GB power system; contractual renewable supply depends on certificate ownership and disclosure rules.",
        "series": [
            {
                "date": row["datetime"].date().isoformat(),
                "carbon_intensity_gco2_kwh": round(float(row["carbon_intensity_gco2_kwh"]), 1),
                "gas_share": round(float(row["gas_share"]), 1),
                "wind_share": round(float(row["wind_share"]), 1),
                "solar_share": round(float(row["solar_share"]), 1),
                "renewables_share": round(float(row["wind_share"] + row["solar_share"] + row["hydro_share"]), 1),
            }
            for _, row in power.iterrows()
        ],
        "latest_generation_mix": {
            "Gas": round(float(latest["gas_share"]), 1),
            "Wind": round(float(latest["wind_share"]), 1),
            "Solar": round(float(latest["solar_share"]), 1),
            "Nuclear": round(float(latest["nuclear_share"]), 1),
            "Biomass": round(float(latest["biomass_share"]), 1),
            "Hydro": round(float(latest["hydro_share"]), 1),
            "Imports": round(float(latest["imports_share"]), 1),
            "Other": round(float(latest["other_share"]), 1),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Power signal: {carbon_signal}, driven by {driver}.")


if __name__ == "__main__":
    main()
