# Assumptions And Limitations

## Carbon Market Data

- No licensed live carbon market price feed is used.
- EUA values are fetched from official EEX public primary-auction workbooks.
- UK ETS CCM monthly average futures-price context is fetched from the official GOV.UK CCM table.
- UKA prices for the spread and carbon-cost context come from the official GOV.UK CCM monthly average futures price.
- The committed UKA auction CSV is an illustrative sample that deviates 10-34% from official GOV.UK monthly averages (source control SC-008). It feeds only the separately labelled UKA auction-demand fields until it is re-curated from ICE Report Centre.
- The dashboard displays the carbon market comparison period.
- Normal scheduled builds validate the UKA CSV, fetch EEX EUA data and GOV.UK CCM data, then read UKA CSVs as raw inputs; they do not regenerate representative demo data.
- UKA prices are GBP and EUA prices are EUR.
- EUA prices are converted to GBP using the static EUR/GBP assumption in `data/raw/carbon/fx_assumptions.csv` before spread is calculated.
- The UKA-EUA spread is calculated monthly: GOV.UK UKA monthly average futures price versus the volume-weighted monthly average of EEX EUA auction clearing prices. The two legs are related but not identical instruments, so the spread is a GBP-normalised context indicator, not a live tradable spread.
- The static EUR/GBP assumption has a stated validity window; source control SC-009 flags when the comparison period runs beyond it.
- Auction cover ratio is used only where data are available.
- The UKA CSV is not an automated ICE feed and must be re-curated from ICE Report Centre before any UKA auction values are used analytically.
- The dashboard is not a trading tool.

## Power Data

- The MVP fetches recent data from the NESO Carbon Intensity API during the Python build.
- No API key is required.
- The dashboard is static after the build; it does not fetch live data in the browser.
- If the NESO API (or the EEX or GOV.UK source) is unavailable, the build keeps the previous extract, records the failure in `data/processed/build_status.json`, flags it on the dashboard (source control SC-010), and exits non-zero. It never substitutes fake data.
- The power module is a fundamentals context layer, not a dispatch forecast.
- Carbon intensity is physical grid emissions context and is not equivalent to contractual renewable supply.

## REGO Data

- The certificate ledger is representative demo supplier-style operating data.
- Contracts are representative demo customer contracts.
- Bad records are intentionally injected to demonstrate controls.
- Public scheme reports provide context but do not provide certificate-level supplier allocations or customer contract mappings.

## Replacement Prices

- Replacement REGO prices are assumptions stored in the representative demo contract file.
- Estimated exposure is calculated as shortfall MWh multiplied by assumed price.
- The exposure estimate is an operational prioritisation input, not a price forecast.

## Advice Boundary

This project is not trading advice, legal advice, compliance advice, or audit sign-off. It is a public portfolio demonstration of analyst workflow design, data controls, and reconciliation logic.
