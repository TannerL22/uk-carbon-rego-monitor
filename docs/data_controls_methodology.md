# Data Controls Methodology

The source register is maintained in `data/source_register.csv` and validated by `src/source_controls.py`.

## Source Lineage

Each dataset is registered with a source ID, dataset name, owner, source type, source URL, manual/API flag, download date, publication date, data period, use case, and known limitations. The EEX, GOV.UK CCM, and NESO source rows are updated during the Python build when those public sources are fetched.

## Controls

| Control ID | Control | Severity | Logic |
| --- | --- | ---: | --- |
| SC-001 | Missing source URL | Medium | source_url blank for non-demo, non-assumption source |
| SC-002 | Missing downloaded_at | Medium | downloaded_at blank |
| SC-003 | Missing data period | Medium | data_period_start or data_period_end blank |
| SC-004 | Stale source | Low | downloaded_at older than freshness threshold |
| SC-005 | Manual entry without note | Medium | manual_or_api is manual and known_limitations blank |
| SC-006 | Missing source owner | Low | source_owner blank |
| SC-007 | Data period mismatch | Medium | data period does not overlap analysis period |

## Output

The source control output is written to `data/processed/source_quality_summary.json`. The dashboard surfaces source count, warning count, stale source count, manual-source note gaps, and the full issue register.

## Rationale

The source register is a credibility feature. It shows that the monitor is not only producing charts; it is also tracking lineage, freshness, manual inputs, and known limitations.
