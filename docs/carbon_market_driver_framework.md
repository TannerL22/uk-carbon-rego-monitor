# Carbon Market Driver Framework

The carbon module is a market-intelligence context layer. It is not a trading terminal and does not use licensed live UKA/EUA price feeds.

## Inputs

- `data/raw/carbon/uk_ets_ccm_monthly_prices.csv`: official GOV.UK UK ETS CCM table (UKA monthly average futures price, trigger price, triggered status).
- `data/raw/carbon/eua_auction_results.csv`: official EEX EU ETS1 primary auction results.
- `data/raw/carbon/uka_auction_results.csv`: UKA auction input. The committed file is an illustrative sample (it fails the SC-008 cross-check against official GOV.UK averages) and is used only for the separately labelled UKA auction-demand fields until it is re-curated from ICE.
- `data/raw/carbon/eua_auction_results_sample.csv` as a fallback demo-seed input only

The normal dashboard build validates the UKA CSV, fetches official EEX EUA public auction workbooks into `data/raw/carbon/eua_auction_results.csv`, and fetches GOV.UK UK ETS CCM monthly tables into `data/raw/carbon/uk_ets_ccm_monthly_prices.csv`. EEX renamed its 2026 worksheet from "Primary Market Auction" to "EU ETS1"; the parser locates the auction sheet by its header row and always skips EU ETS2 sheets, which are a separate market. It does not regenerate representative demo records. Use `python src/seed_demo_data.py` only when intentionally resetting the demo/sample input files.

## Metrics

- Latest UKA monthly average price (GOV.UK CCM table).
- Latest EUA monthly average auction price (volume-weighted EEX EU ETS1 clearing prices).
- Latest EUA monthly average converted into GBP.
- UKA-EUA spread in GBP, by month.
- Trailing average spread (previous six months, excluding the latest month).
- Spread z-score.
- Spread regime.
- EUA auction volume and demand signal using cover ratio (headline).
- UKA auction demand fields, labelled with their provenance.
- Latest GOV.UK UK ETS CCM trigger price and triggered status.

## Spread Regime

```text
spread_gbp_z_score > 1.0  -> UKA premium wider (or discount narrower) than recent average
spread_gbp_z_score < -1.0 -> UKA discount wider (or premium narrower) than recent average
otherwise                 -> broadly stable
```

UKA prices are denominated in GBP. EUA prices are denominated in EUR. The pipeline converts EUA prices into GBP using the static EUR/GBP assumption in `data/raw/carbon/fx_assumptions.csv` before calculating spread. The spread compares the two markets month by month, using only months where both the GOV.UK UKA average and EEX EUA auctions are published. The UKA leg is a futures monthly average and the EUA leg is an auction-clearing monthly average, so the spread is a transparent context indicator, not a live tradable spread.

Each GOV.UK CCM row is labelled with its assessment month; the final average price in that row belongs to the previous calendar month (the end of the monitoring window). The fetcher records this as `price_month`, and all UKA prices are labelled with the month they actually cover.

The dashboard displays the carbon market comparison period so monthly averages are not presented as live market data.

## Auction Demand Signal

```text
latest cover ratio > average of previous 10 auctions + 0.15 -> stronger demand
latest cover ratio < average of previous 10 auctions - 0.15 -> weaker demand
otherwise                                    -> neutral
missing cover ratio                          -> data insufficient
```

## Interpretation

The carbon signal helps frame market conditions for an analyst. It does not determine whether renewable supply can be claimed. That evidence comes from certificate ownership, eligibility, allocation, retirement, and disclosure controls.

## Dashboard Framing

The dashboard separates carbon data into three concepts:

1. Official price signal: GOV.UK UKA monthly averages compared with EEX EUA monthly auction averages.
2. Official UKA monthly context: GOV.UK UK ETS CCM monthly average futures price, trigger price, and triggered status.
3. Optional market reference: a Trading Economics EU Carbon Permits reference can be fetched during the Python/GitHub Actions build when an API secret is configured. It remains separate from official auction and policy inputs.

This keeps auction clearing prices, policy trigger context, and any future market reference data visibly distinct.

## Optional Trading Economics Reference

`src/fetch_tradingeconomics_reference.py` writes `data/processed/carbon_market_reference.json` on every build. If `TRADING_ECONOMICS_API_KEY` is not configured, the output explicitly marks the reference as unavailable and the dashboard shows that no third-party source is loaded.

When the secret is configured, the script fetches the EU Carbon Permits market symbol `EECXM:IND` from Trading Economics' market historical endpoint, writes a raw CSV under `data/raw/carbon/trading_economics_eu_carbon_reference.csv`, and adds a source-register row. This data is labelled as a third-party market reference, not an official exchange feed and not a substitute for EEX, ICE, or GOV.UK sources.

## ICAP Allowance Price Explorer Assessment

The ICAP Allowance Price Explorer was assessed as a possible future cross-ETS market-reference source. It is not integrated into the MVP because the visible data route appears to be an internal application endpoint rather than a documented ingestion API, and the official terms require care around reproduction, redistribution, and original-source restrictions.

See `docs/icap_allowance_price_explorer_assessment.md` for the Phase 7 assessment.
