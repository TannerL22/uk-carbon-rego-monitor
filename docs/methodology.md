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

The dashboard presents carbon data in three distinct layers: official auction signal, official UKA CCM monthly context, and an optional third-party market reference. The optional Trading Economics reference is populated only during the Python/GitHub Actions build when an API secret is configured. It is labelled separately so the project does not imply that official auction data, policy-context tables, and third-party market references are equivalent.

The dashboard deliberately avoids live trading language. Auction and CCM data are used as transparent market-context proxies, not as substitutes for licensed price feeds, internal trading marks, or live FX-adjusted market data. The dashboard displays the carbon market comparison period.

Normal dashboard builds validate the manually curated ICE UKA auction CSV, fetch official EEX EUA public auction data and official GOV.UK CCM tables, then read the UKA auction CSV in `data/raw/carbon/` as a controlled source input. The separate `python src/seed_demo_data.py` command is only for intentionally resetting representative demo inputs.

## GB Power Fundamentals

The power module fetches recent data from the NESO Carbon Intensity API during the Python build. It calculates latest carbon intensity, recent average carbon intensity, gas share, wind and solar share, low-carbon share, and a simple driver label.

Driver logic is intentionally explainable:

```text
if latest gas share is above recent average:
    driver = higher gas share
elif renewable share is below recent average:
    driver = lower renewable output
else:
    driver = mixed generation effects
```

This section distinguishes physical emissions from contractual renewable supply. Carbon intensity describes the grid mix; REGO ownership and disclosure evidence describe contractual claims. If the NESO API or network is unavailable, the build fails clearly rather than substituting fallback data.

## REGO Reconciliation

Representative demo contracts and certificate records are generated to mimic messy supplier-style operating data. The ledger includes intentional errors such as missing IDs, duplicate IDs, lifecycle conflicts, invalid contracts, missing generation/issue/quantity fields, invalid quantity values, technology mismatches, vintage breaches, stale available inventory, and missing source lineage.

The carbon and power sections use public data or curated public extracts. The REGO reconciliation module uses a representative demo ledger because certificate-level supplier allocations and customer contract mappings are internal operating data, not a public dataset.

## Customer Claim Coverage

The customer claim coverage layer reads representative customer/product claim contracts and joins them to the REGO contract summary and exception register. For each contract it calculates contracted MWh, eligible matched REGO MWh, coverage percentage, uncovered MWh, invalid or excluded MWh, surplus MWh, and assumed cover cost.

Claim status is intentionally simple and auditable:

- Covered: eligible REGO coverage is at or above 100% and no contract-scoped exceptions affect the claim.
- Review: coverage is sufficient or the uncovered volume is immaterial, but non-blocking issues require analyst review.
- Shortfall: uncovered MWh is material and no high-severity claim-blocking evidence issue is driving the result.
- Not supportable: contract-scoped high-severity evidence issues affect the claim and the claim is not fully supported by eligible evidence.

GB power intensity, FMD context, Scope 2 context, and UK ETS prices do not determine claim validity. They are context layers only.

## FMD And Emissions-Reporting Context

The FMD module reads a curated GOV.UK Fuel Mix Disclosure table for the 2024-25 disclosure period. It calculates context values for representative customer contracts:

- Location-based emissions proxy using the UK generation-average factor.
- FMD UK mix attribute context using the disclosed fuel-mix percentages.
- Uncovered residual-mix context using uncovered MWh and the residual-mix factor.

These values are reporting context only. They do not calculate official customer Scope 2 emissions, do not certify a market-based emissions figure, and do not affect renewable claim status.

The control engine creates an exception register and a contract summary. The contract summary calculates eligible matched MWh, ineligible allocated MWh, shortfall, surplus, assumed replacement price, and estimated exposure.

## What The Project Does Not Claim

The project does not provide trading advice, legal advice, compliance sign-off, live carbon prices, or real REGO inventory. It demonstrates an analyst workflow and control framework using transparent public, curated, and representative demo data.
