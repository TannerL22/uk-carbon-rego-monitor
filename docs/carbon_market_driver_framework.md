# Carbon Market Driver Framework

The carbon module is a market-intelligence context layer. It is not a trading terminal and does not use licensed live UKA/EUA price feeds.

## Inputs

- `data/raw/carbon/uka_auction_results_sample.csv`
- `data/raw/carbon/eua_auction_results.csv`
- `data/raw/carbon/uk_ets_ccm_monthly_prices.csv`
- `data/raw/carbon/eua_auction_results_sample.csv` as a fallback demo-seed input only

Fields include market, auction date, auction volume, clearing price, currency, cover ratio, reference price, source, URL, and notes.

The normal dashboard build fetches official EEX EUA public auction workbooks into `data/raw/carbon/eua_auction_results.csv`, fetches GOV.UK UK ETS CCM monthly tables into `data/raw/carbon/uk_ets_ccm_monthly_prices.csv`, and reads UKA auction inputs from the curated/manual CSV. It does not regenerate representative demo records. Use `python src/seed_demo_data.py` only when intentionally resetting the demo/sample input files.

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

The dashboard displays the carbon market comparison period so curated/manual UKA inputs are not presented as live market data.

## Auction Demand Signal

```text
latest cover ratio > trailing average + 0.15 -> stronger demand
latest cover ratio < trailing average - 0.15 -> weaker demand
otherwise                                    -> neutral
missing cover ratio                          -> data insufficient
```

## Interpretation

The carbon signal helps frame market conditions for an analyst. It does not determine whether renewable supply can be claimed. That evidence comes from certificate ownership, eligibility, allocation, retirement, and disclosure controls.
