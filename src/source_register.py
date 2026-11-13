"""Read and update ``data/source_register.csv`` from fetch/validation scripts.

Several scripts refresh their own row in the source register. Keeping the CSV
handling in one place guarantees a stable column order, consistent ``\\n`` line
endings (so scheduled refreshes do not churn the whole file), and that a script
only ever replaces the row carrying its own ``source_id``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from project_paths import ROOT


SOURCE_REGISTER = ROOT / "data" / "source_register.csv"

FIELDNAMES = [
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


def read_register(path: Path = SOURCE_REGISTER) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_register(rows: list[dict[str, str]], path: Path = SOURCE_REGISTER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") or "" for field in FIELDNAMES})


def upsert_source(source_row: dict[str, object], path: Path = SOURCE_REGISTER) -> None:
    """Replace the row with the same ``source_id`` (keeping its position) or append it."""

    source_id = str(source_row["source_id"])
    rows = read_register(path)
    merged = {field: str(source_row.get(field, "") or "") for field in FIELDNAMES}
    for index, row in enumerate(rows):
        if row.get("source_id") == source_id:
            rows[index] = merged
            break
    else:
        rows.append(merged)
    write_register(rows, path)


def update_source_fields(source_id: str, updates: dict[str, object], path: Path = SOURCE_REGISTER) -> None:
    """Update selected fields on an existing row; no-op when the row is absent."""

    rows = read_register(path)
    changed = False
    for row in rows:
        if row.get("source_id") == source_id:
            row.update({key: str(value) for key, value in updates.items()})
            changed = True
    if changed:
        write_register(rows, path)
