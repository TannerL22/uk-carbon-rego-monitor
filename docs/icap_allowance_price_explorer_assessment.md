# ICAP Allowance Price Explorer Assessment

Assessed: 2026-05-03

## Recommendation

Do not integrate the ICAP Allowance Price Explorer into the automated MVP data pipeline at this stage.

ICAP is a useful external reference for cross-ETS allowance-price context, but it should remain a future research/reference source until licensing, redistribution permissions, and API stability are confirmed. The current dashboard should continue to use official auction and policy sources as the carbon-market backbone:

- EEX EUA primary auction reports.
- Manually curated ICE UKA auction results.
- GOV.UK UK ETS CCM monthly price context.

## What Was Checked

- Public ICAP Allowance Price Explorer page: https://icapcarbonaction.com/en/ets/ets-prices
- Embedded explorer application: https://allowancepriceexplorer.icapcarbonaction.com
- Terms and documentation page: https://icapcarbonaction.com/en/documentation-allowance-price-explorer

The embedded explorer loads a JSON endpoint at:

```text
https://allowancepriceexplorer.icapcarbonaction.com/api/systems
```

That endpoint is technically accessible and contains a large cross-system dataset used by the browser application. However, it appears to be an internal application endpoint rather than a documented, versioned public API for scheduled data ingestion.

## Key Risks

1. Licensing and redistribution constraints

   ICAP's documentation says graphics or underlying data may only be reproduced, redistributed, or used for non-commercial purposes subject to prior written permission. That makes automatic download, storage, and redistribution through this public GitHub Pages project inappropriate without explicit permission.

2. Original-source restrictions

   ICAP's documentation identifies original data sources and includes specific restrictions for some exchange data, including ICE data. Those restrictions matter because this project would be republishing generated CSV/JSON files through GitHub Pages.

3. Manual update frequency

   ICAP states that allowance prices and revenues are updated manually and quarterly. That is useful for context, but it does not solve the desire for a regularly refreshed carbon-market signal.

4. API stability

   The discoverable JSON route is used by the frontend application, but it is not presented as a stable API contract. Building a scheduled GitHub Action around it would create a brittle dependency.

## Suitable Future Uses

ICAP could still be useful in one of these controlled ways:

- Add an external reference link in the dashboard or README.
- Use ICAP manually for analyst research, with source citation.
- Revisit automated ingestion only after confirming permission and acceptable terms.
- Keep any ICAP-derived data separate from official auction signals and clearly label it as a third-party market reference.

## Implementation Decision

No ICAP code integration was added in Phase 7. The dashboard's optional market-reference layer should only be populated by sources that are separately permissioned, technically stable, and clearly labelled.
