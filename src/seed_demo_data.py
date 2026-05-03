"""Seed deterministic representative demo inputs for the monitor.

This script is intentionally separate from the normal dashboard build. Use it
only when resetting the representative REGO/contracts demo data or the initial
curated/sample carbon input files.

The scheduled/static-site refresh path should run ``python src/build_all.py``,
which reads raw inputs and does not overwrite curated carbon CSVs.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SOURCE_REGISTER = ROOT / "data" / "source_register.csv"


def ensure_directories() -> None:
    for path in [
        RAW / "rego",
        RAW / "carbon",
        RAW / "power",
        PROCESSED,
        ROOT / "outputs",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_contracts() -> list[dict[str, object]]:
    return [
        {
            "contract_id": "C-001",
            "counterparty": "Corporate Buyer A",
            "product_type": "Wind-backed renewable supply",
            "contract_start": "2024-04-01",
            "contract_end": "2025-03-31",
            "delivery_period_start": "2024-04-01",
            "delivery_period_end": "2025-03-31",
            "required_mwh": 12000,
            "eligible_technology": "Wind",
            "eligible_country": "GB",
            "fmd_period": "2024-25",
            "contract_status": "Signed",
            "assumed_rego_replacement_price_gbp_per_mwh": 6.50,
        },
        {
            "contract_id": "C-002",
            "counterparty": "Corporate Buyer B",
            "product_type": "Solar-backed renewable supply",
            "contract_start": "2024-04-01",
            "contract_end": "2025-03-31",
            "delivery_period_start": "2024-04-01",
            "delivery_period_end": "2025-03-31",
            "required_mwh": 8000,
            "eligible_technology": "Solar",
            "eligible_country": "GB",
            "fmd_period": "2024-25",
            "contract_status": "Signed",
            "assumed_rego_replacement_price_gbp_per_mwh": 7.25,
        },
        {
            "contract_id": "C-003",
            "counterparty": "FMD Pool",
            "product_type": "Standard renewable supply",
            "contract_start": "2024-04-01",
            "contract_end": "2025-03-31",
            "delivery_period_start": "2024-04-01",
            "delivery_period_end": "2025-03-31",
            "required_mwh": 20000,
            "eligible_technology": "Any Renewable",
            "eligible_country": "GB",
            "fmd_period": "2024-25",
            "contract_status": "Open",
            "assumed_rego_replacement_price_gbp_per_mwh": 5.75,
        },
    ]


def certificate_row(
    certificate_id: str,
    index: int,
    technology: str,
    contract_id: str,
    counterparty: str,
    quantity_mwh: float | str,
    status: str = "Retired",
    country: str = "GB",
    generation_start: str | None = None,
    generation_end: str | None = None,
    issue_date: str | None = None,
    received_date: str | None = None,
    allocated_date: str | None = None,
    retired_date: str | None = None,
    last_updated: str | None = None,
    source_file: str = "synthetic_rego_ledger.csv",
) -> dict[str, object]:
    month_start = date(2024, 4, 1) + timedelta(days=(index % 12) * 30)
    gen_start = generation_start if generation_start is not None else month_start.isoformat()
    gen_end = generation_end if generation_end is not None else (month_start + timedelta(days=29)).isoformat()
    issue = issue_date if issue_date is not None else (month_start + timedelta(days=45)).isoformat()
    received = received_date if received_date is not None else (month_start + timedelta(days=50)).isoformat()
    allocated = allocated_date if allocated_date is not None else "2025-03-20"
    retired = retired_date if retired_date is not None else "2025-06-15"
    updated = last_updated or "2025-03-30"

    return {
        "certificate_id": certificate_id,
        "batch_id": f"BATCH-{technology[:3].upper()}-{index // 10:03d}",
        "asset_name": f"{technology} Asset {index % 9 + 1}",
        "technology": technology,
        "country": country,
        "generation_start": gen_start,
        "generation_end": gen_end,
        "issue_date": issue,
        "received_date": received,
        "allocated_date": allocated,
        "retired_date": retired,
        "status": status,
        "quantity_mwh": quantity_mwh,
        "counterparty": counterparty,
        "contract_id": contract_id,
        "account": "REGO Operating Account",
        "last_updated": updated,
        "source_file": source_file,
    }


def generate_rego_ledger() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for idx in range(47):
        rows.append(certificate_row(f"REG-WIND-{idx + 1:04d}", idx, "Wind", "C-001", "Corporate Buyer A", 250))
    rows.append(certificate_row("REG-WIND-0048", 48, "Wind", "C-001", "Corporate Buyer A", 100))

    for idx in range(29):
        rows.append(certificate_row(f"REG-SOLAR-{idx + 1:04d}", idx, "Solar", "C-002", "Corporate Buyer B", 250))

    for idx in range(83):
        technology = ["Wind", "Solar", "Hydro", "Biomass"][idx % 4]
        rows.append(certificate_row(f"REG-POOL-{idx + 1:04d}", idx, technology, "C-003", "FMD Pool", 250))
    rows.append(certificate_row("REG-POOL-0084", 84, "Hydro", "C-003", "FMD Pool", 150))

    bad_rows = [
        certificate_row("", 200, "Wind", "", "", 50, status="Available", allocated_date="", retired_date=""),
        certificate_row("REG-DUP-0001", 201, "Wind", "C-001", "Corporate Buyer A", 75),
        certificate_row("REG-DUP-0001", 202, "Wind", "C-001", "Corporate Buyer A", 75),
        certificate_row("REG-BAD-0001", 203, "Solar", "C-002", "Corporate Buyer B", 100, issue_date="2025-02-10", retired_date="2025-01-15"),
        certificate_row("REG-BAD-0002", 204, "Wind", "", "Corporate Buyer A", 100, status="Allocated", retired_date=""),
        certificate_row("REG-BAD-0003", 205, "Wind", "C-999", "Unknown Buyer", 100),
        certificate_row("REG-BAD-0004", 206, "Wind", "C-002", "Corporate Buyer B", 100),
        certificate_row("REG-BAD-0005", 207, "Wind", "C-001", "Corporate Buyer A", 100, generation_start="2025-04-01", generation_end="2025-04-30"),
        certificate_row("REG-BAD-0006", 208, "Wind", "C-001", "Corporate Buyer A", 100, country="IE"),
        certificate_row("REG-BAD-0007", 209, "Solar", "C-002", "Corporate Buyer B", 100, status="Available", allocated_date="", retired_date="", source_file=""),
        certificate_row("REG-BAD-0008", 210, "Wind", "", "", 100, status="Available", allocated_date="", retired_date="", last_updated="2024-09-01"),
        certificate_row("REG-BAD-0009", 211, "Wind", "C-003", "FMD Pool", 1, generation_start="", generation_end="2024-10-27"),
        certificate_row("REG-BAD-0010", 212, "Solar", "C-003", "FMD Pool", 1, issue_date=""),
        certificate_row("REG-BAD-0011", 213, "Hydro", "C-003", "FMD Pool", ""),
        certificate_row("REG-BAD-0012", 214, "Biomass", "C-003", "FMD Pool", "not_available"),
    ]
    rows.extend(bad_rows)
    return rows


def generate_carbon_auction_samples() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    uka_prices = [42.2, 43.4, 41.8, 40.7, 39.6, 38.9, 37.8, 36.4, 35.9, 35.1, 34.6, 33.8]
    eua_prices = [66.1, 66.8, 65.4, 64.9, 65.7, 66.5, 67.1, 68.2, 68.9, 69.5, 70.1, 70.7]
    start = date(2024, 10, 3)
    uka_rows: list[dict[str, object]] = []
    eua_rows: list[dict[str, object]] = []
    for idx, (uka, eua) in enumerate(zip(uka_prices, eua_prices)):
        auction_date = start + timedelta(days=idx * 21)
        uka_rows.append(
            {
                "market": "UKA",
                "auction_date": auction_date.isoformat(),
                "auction_volume": 2450000 + idx * 15000,
                "clearing_price": uka,
                "currency": "GBP",
                "cover_ratio": round(1.42 - idx * 0.018, 2),
                "reference_price": round(uka + (0.5 if idx < 6 else -0.3), 2),
                "source": "Curated public auction sample",
                "source_url": "https://www.gov.uk/government/collections/uk-emissions-trading-scheme",
                "notes": "Sample values for public portfolio demonstration",
            }
        )
        eua_rows.append(
            {
                "market": "EUA",
                "auction_date": auction_date.isoformat(),
                "auction_volume": 3200000 + idx * 22000,
                "clearing_price": eua,
                "currency": "EUR",
                "cover_ratio": round(1.78 + idx * 0.01, 2),
                "reference_price": round(eua - 0.2, 2),
                "source": "Curated public auction sample",
                "source_url": "https://climate.ec.europa.eu/eu-action/eu-emissions-trading-system-eu-ets_en",
                "notes": "Sample values for public portfolio demonstration",
            }
        )
    return uka_rows, eua_rows


def generate_fx_assumptions() -> list[dict[str, object]]:
    return [
        {
            "currency_pair": "EURGBP",
            "rate": 0.86,
            "rate_basis": "Illustrative static FX assumption for converting EUA EUR auction prices into GBP",
            "valid_from": "2024-10-01",
            "valid_to": "2025-05-31",
            "source": "Project assumption",
            "notes": "Used for public demo only; not a live FX feed",
        }
    ]


def generate_source_register() -> list[dict[str, object]]:
    return [
        {
            "source_id": "SRC-001",
            "dataset_name": "Representative demo REGO ledger",
            "source_owner": "Project representative demo data",
            "source_type": "representative demo",
            "source_url": "",
            "manual_or_api": "manual",
            "downloaded_at": "2025-03-31",
            "published_at": "2025-03-31",
            "data_period_start": "2024-04-01",
            "data_period_end": "2025-03-31",
            "used_for": "REGO reconciliation controls",
            "known_limitations": "Representative supplier-style operating ledger for demo control testing; not real customer data",
        },
        {
            "source_id": "SRC-002",
            "dataset_name": "Representative demo contracts",
            "source_owner": "Project representative demo data",
            "source_type": "representative demo",
            "source_url": "",
            "manual_or_api": "manual",
            "downloaded_at": "2025-03-31",
            "published_at": "2025-03-31",
            "data_period_start": "2024-04-01",
            "data_period_end": "2025-03-31",
            "used_for": "Contract coverage and exposure assumptions",
            "known_limitations": "Representative demo contracts with assumed replacement REGO prices; not real customer terms",
        },
        {
            "source_id": "SRC-003",
            "dataset_name": "UKA auction results sample",
            "source_owner": "UK ETS Authority / curated sample",
            "source_type": "public sample",
            "source_url": "https://www.gov.uk/government/collections/uk-emissions-trading-scheme",
            "manual_or_api": "manual",
            "downloaded_at": "",
            "published_at": "2025-03-20",
            "data_period_start": "2024-10-03",
            "data_period_end": "2025-05-22",
            "used_for": "Carbon market signal",
            "known_limitations": "Curated sample values, not a licensed live price feed",
        },
        {
            "source_id": "SRC-004",
            "dataset_name": "EUA auction results sample",
            "source_owner": "European Commission / curated sample",
            "source_type": "public sample",
            "source_url": "https://climate.ec.europa.eu/eu-action/eu-emissions-trading-system-eu-ets_en",
            "manual_or_api": "manual",
            "downloaded_at": "2025-03-31",
            "published_at": "2025-03-20",
            "data_period_start": "2024-10-03",
            "data_period_end": "2025-05-22",
            "used_for": "Carbon market signal",
            "known_limitations": "",
        },
        {
            "source_id": "SRC-005",
            "dataset_name": "NESO Carbon Intensity API",
            "source_owner": "National Energy System Operator",
            "source_type": "public API",
            "source_url": "https://api.carbonintensity.org.uk",
            "manual_or_api": "api",
            "downloaded_at": "",
            "published_at": "",
            "data_period_start": "",
            "data_period_end": "",
            "used_for": "GB power fundamentals",
            "known_limitations": "Fetched from public API during build; build fails clearly if the API is unavailable",
        },
        {
            "source_id": "SRC-006",
            "dataset_name": "EUR/GBP FX assumption",
            "source_owner": "Project assumption",
            "source_type": "assumption",
            "source_url": "",
            "manual_or_api": "manual",
            "downloaded_at": "2025-03-31",
            "published_at": "2025-03-31",
            "data_period_start": "2024-10-01",
            "data_period_end": "2025-05-31",
            "used_for": "EUA EUR to GBP conversion for carbon spread signal",
            "known_limitations": "Static illustrative FX assumption, not a live FX feed",
        },
    ]


def main() -> None:
    ensure_directories()

    contracts = generate_contracts()
    ledger = generate_rego_ledger()
    uka_rows, eua_rows = generate_carbon_auction_samples()
    fx_rows = generate_fx_assumptions()
    source_rows = generate_source_register()

    write_csv(RAW / "rego" / "synthetic_contracts.csv", contracts, list(contracts[0].keys()))
    write_csv(RAW / "rego" / "synthetic_rego_ledger.csv", ledger, list(ledger[0].keys()))
    write_csv(RAW / "carbon" / "uka_auction_results_sample.csv", uka_rows, list(uka_rows[0].keys()))
    write_csv(RAW / "carbon" / "eua_auction_results_sample.csv", eua_rows, list(eua_rows[0].keys()))
    write_csv(RAW / "carbon" / "fx_assumptions.csv", fx_rows, list(fx_rows[0].keys()))
    write_csv(SOURCE_REGISTER, source_rows, list(source_rows[0].keys()))

    print(f"Generated {len(contracts)} contracts and {len(ledger)} REGO ledger records.")


if __name__ == "__main__":
    main()
