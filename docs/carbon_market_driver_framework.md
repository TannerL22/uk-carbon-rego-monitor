# Carbon Market Driver Framework

The carbon module is a market-intelligence context layer. It is not a trading terminal and does not use licensed live UKA/EUA price feeds.

## Inputs

- `data/raw/carbon/uka_auction_results.csv`
- `data/raw/carbon/eua_auction_results.csv`
- `data/raw/carbon/uk_ets_ccm_monthly_prices.csv`
- `data/raw/carbon/eua_auction_results_sample.csv` as a fallback demo-seed input only

Fields include market, auction date, auction volume, clearing price, currency, cover ratio, reference price, source, URL, and notes.

The normal dashboard build validates the manually curated ICE UKA CSV, fetches official EEX EUA public auction workbooks into `data/raw/carbon/eua_auction_results.csv`, fetches GOV.UK UK ETS CCM monthly tables into `data/raw/carbon/uk_ets_ccm_monthly_prices.csv`, and reads the validated UKA auction input. It does not regenerate representative demo records. Use `python src/seed_demo_data.py` only when intentionally resetting the demo/sample input files.

## Metrics

- Latest UKA auction price.
- Latest EUA auction price.
- Latest EUA auction price converted into GBP.
- UKA-EUA spread in GBP.
- Trailing average spread.
- Spread z-score.
- Spread regime.
- Auction volume.
- Auction demand signal using cover ratio where available.
- Latest GOV.UK UK ETS CCM monthly average futures price.
- Latest GOV.UK UK ETS CCM trigger price and triggered status.

## Spread Regime

```text
spread_gbp_z_score > 1.0  -> UKA premium wider than recent average
spread_gbp_z_score < -1.0 -> UKA discount wider than recent average
otherwise                 -> broadly stable
```

UKA prices are denominated in GBP. EUA prices are denominated in EUR. The pipeline converts EUA prices into GBP using the static EUR/GBP assumption in `data/raw/carbon/fx_assumptions.csv` before calculating spread. Because official EEX and UKA auction calendars differ, UKA dates are aligned to the nearest EUA auction date within 14 days. The spread is a simplified auction-context indicator and should not be interpreted as a live tradable spread.

GOV.UK CCM monthly average futures prices are separate from auction clearing prices. They are included as official UKA policy and price-context evidence, not as a replacement for auction data or a live market feed.

The dashboard displays the carbon market comparison period so manually curated UKA inputs are not presented as live market data.

## Auction Demand Signal

```text
latest cover ratio > trailing average + 0.15 -> stronger demand
latest cover ratio < trailing average - 0.15 -> weaker demand
otherwise                                    -> neutral
missing cover ratio                          -> data insufficient
```

## Interpretation

The carbon signal helps frame market conditions for an analyst. It does not determine whether renewable supply can be claimed. That evidence comes from certificate ownership, eligibility, allocation, retirement, and disclosure controls.

## Dashboard Framing

The dashboard separates carbon data into three concepts:

1. Official auction signal: EEX EUA auction results and manually curated ICE UKA auction inputs.
2. Official UKA monthly context: GOV.UK UK ETS CCM monthly average futures price, trigger price, and triggered status.
3. Optional market reference: a Trading Economics EU Carbon Permits reference can be fetched during the Python/GitHub Actions build when an API secret is configured. It remains separate from official auction and policy inputs.

This keeps auction clearing prices, policy trigger context, and any future market reference data visibly distinct.

## Optional Trading Economics Reference

`src/fetch_tradingeconomics_reference.py` writes `data/processed/carbon_market_reference.json` on every build. If `TRADING_ECONOMICS_API_KEY` is not configured, the output explicitly marks the reference as unavailable and the dashboard shows that no third-party source is loaded.

When the secret is configured, the script fetches the EU Carbon Permits market symbol `EECXM:IND` from Trading Economics' market historical endpoint, writes a raw CSV under `data/raw/carbon/trading_economics_eu_carbon_reference.csv`, and adds a source-register row. This data is labelled as a third-party market reference, not an official exchange feed and not a substitute for EEX, ICE, or GOV.UK sources.

## ICAP Allowance Price Explorer Assessment

The ICAP Allowance Price Explorer was assessed as a possible future cross-ETS market-reference source. It is not integrated into the MVP because the visible data route appears to be an internal application endpoint rather than a documented ingestion API, and the official terms require care around reproduction, redistribution, and original-source restrictions.

See `docs/icap_allowance_price_explorer_assessment.md` for the Phase 7 assessment.
