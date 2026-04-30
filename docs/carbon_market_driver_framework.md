# Carbon Market Driver Framework

The carbon module is a market-intelligence context layer. It is not a trading terminal and does not use licensed live UKA/EUA price feeds.

## Inputs

- `data/raw/carbon/uka_auction_results_sample.csv`
- `data/raw/carbon/eua_auction_results_sample.csv`

Fields include market, auction date, auction volume, clearing price, currency, cover ratio, reference price, source, URL, and notes.

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

## Spread Regime

```text
spread_gbp_z_score > 1.0  -> UKA premium wider than recent average
spread_gbp_z_score < -1.0 -> UKA discount wider than recent average
otherwise                 -> broadly stable
```

UKA prices are denominated in GBP. EUA prices are denominated in EUR. The pipeline converts EUA prices into GBP using the static EUR/GBP assumption in `data/raw/carbon/fx_assumptions.csv` before calculating spread. The spread is a simplified public-sample indicator and should not be interpreted as a live tradable spread.

The dashboard displays the carbon market sample period so older curated auction samples are not presented as live market data.

## Auction Demand Signal

```text
latest cover ratio > trailing average + 0.15 -> stronger demand
latest cover ratio < trailing average - 0.15 -> weaker demand
otherwise                                    -> neutral
missing cover ratio                          -> data insufficient
```

## Interpretation

The carbon signal helps frame market conditions for an analyst. It does not determine whether renewable supply can be claimed. That evidence comes from certificate ownership, eligibility, allocation, retirement, and disclosure controls.
