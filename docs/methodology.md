# Methodology

## Purpose

The monitor connects three operating questions:

1. What is the current UK/EU carbon-market backdrop?
2. What is happening physically on the GB power system?
3. Can renewable certificate inventory be matched cleanly against contract obligations and audit requirements?

The third question is the core of the project. Carbon and power signals provide context, while REGO reconciliation determines whether renewable supply claims can be evidenced.

## Carbon Market Signals

The carbon module uses curated public-sample UKA and EUA auction data. UKA prices are denominated in GBP and EUA prices are denominated in EUR, so the pipeline converts EUA prices into GBP using the stated EUR/GBP assumption before calculating the UKA-EUA spread. It calculates latest auction prices, GBP-normalised spread, trailing average spread, spread z-score, auction volume, and a basic auction demand signal using cover ratio where available.

The dashboard deliberately avoids live trading language. Auction data are used as a transparent market-context proxy, not as a substitute for licensed price feeds, internal trading marks, or live FX-adjusted market data. The dashboard displays the carbon market sample period.

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

The project does not provide trading advice, legal advice, compliance sign-off, live carbon prices, or real REGO inventory. It demonstrates an analyst workflow and control framework using transparent sample data.
