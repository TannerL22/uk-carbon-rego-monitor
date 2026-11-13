# Manual UKA Auction CSV Update

`uka_auction_results.csv` is a manually maintained source input. The normal
dashboard build validates it, but does not fetch or overwrite it.

> **Current status: header only.** The file previously held illustrative rows
> carried over from the demo seed; they deviated 10-34% from the official GOV.UK
> UK ETS monthly average prices and were removed in November 2026. A header-only
> file is valid: UKA price and spread signals use the official GOV.UK monthly
> averages, and the dashboard's UKA auction-demand fields show "not loaded".
> ICE publishes results in its Report Centre (browser), not as a documented
> machine-readable feed, so rows must be added manually using the process below.

## Source

- ICE UKA auction page: https://www.ice.com/emissions/auctions/uk-emission-allowances
- ICE UKA auction contract page: https://www.ice.com/products/80216146/UKA-UK-Auction
- UK ETS markets guidance: https://www.gov.uk/government/publications/uk-emissions-trading-scheme-markets

ICE is the appointed UKA auction platform. The project does not claim automated
ICE scraping because a stable public machine-readable endpoint has not been
implemented in this MVP.

## Required Columns

```text
market
auction_date
auction_volume
clearing_price
currency
cover_ratio
reference_price
source
source_url
downloaded_at
manual_update_note
notes
```

## Update Process

1. Review the latest official ICE UKA auction result reference.
2. Add or amend rows in `data/raw/carbon/uka_auction_results.csv`.
3. Keep `market` as `UKA` and `currency` as `GBP`.
4. Populate `downloaded_at` with the manual update date in `YYYY-MM-DD` format.
5. Keep the source and notes fields explicit about manual curation, and do
   not use the words "illustrative", "sample" or "not verified" for real ICE
   rows: the validator uses them to label the register entry as illustrative.
6. Run:

```bash
python src/validate_uka_auction_input.py
python src/build_all.py
```

7. Check `data/processed/source_quality_summary.json`: SC-008 should no longer
   be raised. Each auction clearing price should sit within 10% of the official
   GOV.UK monthly average for its month.

## Limitation

Once curated, this file is a manual extract from official ICE references, not
a live ICE feed. Check it against ICE Report Centre before external analytical
use.
