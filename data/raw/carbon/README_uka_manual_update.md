# Manual UKA Auction CSV Update

`uka_auction_results.csv` is a manually maintained source input. The normal
dashboard build validates it, but does not fetch or overwrite it.

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
5. Keep the source and notes fields explicit about manual curation.
6. Run:

```bash
python src/validate_uka_auction_input.py
python src/build_all.py
```

## Limitation

This file is manually curated from official ICE references. It is not a live
ICE feed and should be checked against ICE Report Centre before external
analytical use.
