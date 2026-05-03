# Methodology

## Purpose

The monitor connects three operating questions:

1. What is the current UK/EU carbon-market backdrop?
2. What is happening physically on the GB power system?
3. Can renewable certificate inventory be matched cleanly against contract obligations and audit requirements?

The third question is the core of the project. Carbon and power signals provide context, while REGO reconciliation determines whether renewable supply claims can be evidenced.

## Carbon Market Signals

The carbon module uses official EEX EUA primary-auction data, manually curated ICE UKA auction inputs, and official GOV.UK UK ETS Cost Containment Mechanism tables. UKA prices are denominated in GBP and EUA prices are denominated in EUR, so the pipeline converts EUA prices into GBP using the stated EUR/GBP assumption before calculating the UKA-EUA spread. Because official EEX and UKA auction calendars differ, UKA auction dates are aligned to the nearest EUA auction date within 14 days. It calculates latest auction prices, GBP-normalised spread, trailing average spread, spread z-score, auction volume, and a basic auction demand signal using cover ratio where available.

The GOV.UK CCM parser adds official monthly average UKA futures-price context, trigger price, and triggered status. This is shown separately from auction clearing prices because it is a policy/market-context table, not an auction result.

The dashboard presents carbon data in three distinct layers: official auction signal, official UKA CCM monthly context, and an optional market-reference placeholder. The optional market-reference layer is deliberately not populated in the MVP so the project does not imply a live third-party market feed where none exists.

The dashboard deliberately avoids live trading language. Auction and CCM data are used as transparent market-context proxies, not as substitutes for licensed price feeds, internal trading marks, or live FX-adjusted market data. The dashboard displays the carbon market comparison period.

Normal dashboard builds validate the manually curated ICE UKA auction CSV, fetch official EEX EUA public auction data and official GOV.UK CCM tables, then read the UKA auction CSV in `data/raw/carbon/` as a controlled source input. The separate `python src/seed_demo_data.py` command is only for intentionally resetting representative demo inputs.

## GB Power Fundamentals

The power module fetches recent live data from the NESO Carbon Intensity API during the Python build. It calculates latest carbon intensity, recent average carbon intensity, gas share, wind and solar share, low-carbon share, and a simple driver label.

Driver logic is intentionally explainable:

```text
if latest gas share is above recent average:
    driver = higher gas share
elif renewable share is below recent average:
    driver = lower renewable output
else:
    driver = mixed generation effects
```

This section distinguishes physical emissions from contractual renewable supply. Carbon intensity describes the grid mix; REGO ownership and disclosure evidence describe contractual claims. If the NESO API or network is unavailable, the build fails clearly rather than substituting fake live data.

## REGO Reconciliation

Representative demo contracts and certificate records are generated to mimic messy supplier-style operating data. The ledger includes intentional errors such as missing IDs, duplicate IDs, lifecycle conflicts, invalid contracts, technology mismatches, vintage breaches, stale available inventory, and missing source lineage.

The carbon and power sections use public data or curated public extracts. The REGO reconciliation module uses a representative demo ledger because certificate-level supplier allocations and customer contract mappings are internal operating data, not a public dataset.

The control engine creates an exception register and a contract summary. The contract summary calculates eligible matched MWh, ineligible allocated MWh, shortfall, surplus, assumed replacement price, and estimated exposure.

## What The Project Does Not Claim

The project does not provide trading advice, legal advice, compliance sign-off, live carbon prices, or real REGO inventory. It demonstrates an analyst workflow and control framework using transparent public, curated, and representative demo data.
