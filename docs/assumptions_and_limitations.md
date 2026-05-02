# Assumptions And Limitations

## Carbon Market Data

- No licensed live carbon market price feed is used.
- EUA values are fetched from official EEX public primary-auction workbooks.
- UK ETS CCM monthly average futures-price context is fetched from the official GOV.UK CCM table.
- UKA values remain curated/manual auction inputs until the official ICE CSV is added.
- The dashboard displays the carbon market comparison period.
- Normal scheduled builds fetch EEX EUA data and GOV.UK CCM data, then read UKA CSVs as raw inputs; they do not regenerate representative demo data.
- UKA prices are GBP and EUA prices are EUR.
- EUA prices are converted to GBP using the static EUR/GBP assumption in `data/raw/carbon/fx_assumptions.csv` before spread is calculated.
- UKA auction dates are aligned to the nearest EUA auction date within 14 days because official auction calendars differ.
- The UKA-EUA spread is a simplified GBP-normalised auction-context indicator, not a live tradable spread.
- GOV.UK CCM monthly average futures prices are not auction clearing prices and should not be mixed with the UKA/EUA auction spread.
- Auction cover ratio is used only where data are available.
- The dashboard is not a trading tool.

## Power Data

- The MVP fetches live recent data from the NESO Carbon Intensity API during the Python build.
- No API key is required.
- The dashboard is static after the build; it does not fetch live data in the browser.
- If the NESO API or local network is unavailable, the build fails clearly.
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
