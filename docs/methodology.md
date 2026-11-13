# Methodology

## Purpose

The monitor connects three operating questions:

1. What is the current UK/EU carbon-market backdrop?
2. What is happening physically on the GB power system?
3. Can renewable certificate inventory be matched cleanly against contract obligations and audit requirements?

The third question is the core of the project. Carbon and power signals provide context, while REGO reconciliation determines whether renewable supply claims can be evidenced.

## Carbon Market Signals

The carbon module compares the official GOV.UK UK ETS Cost Containment Mechanism (CCM) monthly average UKA futures price with the volume-weighted monthly average of official EEX EU ETS1 primary-auction clearing prices. UKA prices are denominated in GBP and EUA prices are denominated in EUR, so the pipeline converts EUA prices into GBP using the ECB monthly average EUR/GBP reference rate for each month before calculating the monthly UKA-EUA spread, trailing average spread (previous six months), spread z-score, and spread regime. The auction demand signal uses EEX EUA cover ratios.

The GOV.UK CCM table also provides the trigger price and triggered status. Each CCM row is labelled with its assessment month, and its final average belongs to the previous calendar month; the pipeline stores that as `price_month` so prices are labelled with the month they cover.

The UKA auction CSV in `data/raw/carbon/` is validated and cross-checked against the official monthly averages (source control SC-008). The committed file is an illustrative sample that fails the cross-check, so it is not used for price or spread signals.

The dashboard presents carbon data in three distinct layers: official monthly price signal, official UKA CCM policy context, and an optional third-party market reference. The optional Trading Economics reference is populated only during the Python/GitHub Actions build when an API secret is configured. It is labelled separately so the project does not imply that official auction data, policy-context tables, and third-party market references are equivalent.

The dashboard deliberately avoids live trading language. Monthly CCM averages and auction data are used as transparent market-context proxies, not as substitutes for licensed price feeds, internal trading marks, or live FX-adjusted market data. The dashboard displays the carbon market comparison period.

Normal dashboard builds validate the UKA auction CSV, fetch official EEX EUA public auction data and official GOV.UK CCM tables, then read the UKA auction CSV in `data/raw/carbon/` as a controlled source input. The separate `python src/seed_demo_data.py` command is only for intentionally resetting representative demo inputs.

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

The FMD module reads every GOV.UK Fuel Mix Disclosure table in `data/raw/fmd/` (2024-25 archived extract; 2025-26 fetched by `src/fetch_fmd.py`) and matches each contract to its own disclosure period. It calculates context values for representative customer contracts:

- Location-based emissions proxy using the UK generation-average factor.
- FMD UK mix attribute context using the disclosed fuel-mix percentages.
- Uncovered residual-mix context using uncovered MWh and the residual-mix factor.

These values are reporting context only. They do not calculate official customer Scope 2 emissions, do not certify a market-based emissions figure, and do not affect renewable claim status.

## Carbon-Cost Context

The carbon-cost layer reuses the latest official GOV.UK monthly average UKA price and selected emissions-factor assumptions to produce indicative GBP/MWh context:

```text
indicative carbon cost GBP/MWh = UKA GBP/tCO2 * emissions factor tCO2/MWh
```

This helps frame the wider carbon-cost environment around fossil or residual exposure. It is not a customer bill calculation, not a power-price forecast, not a REGO claim validation input, and not an official customer emissions result. Customer claim status is unchanged if carbon prices move.

## Future Scope 2 Readiness

The future-readiness layer is a data-preparedness view for possible Scope 2 methodology changes. It checks representative customer contracts for annual claim status, generation-period evidence, market-boundary fields, hourly/settlement-period data availability, and deliverability flags.

The readiness output is deliberately separate from current annual REGO claim supportability:

- Current annual claim status is governed by REGO evidence, contract coverage, and contract-scoped controls.
- Future readiness is a Low / Medium / High data-readiness flag.
- The dashboard does not apply final revised Scope 2 rules.
- The dashboard does not calculate 24/7 matching, hourly deliverability, or official customer Scope 2 emissions.

This keeps future reporting risk visible without overstating what the representative data can support.

## Claim Evidence Register

The claim evidence register converts certificate-control exceptions into an operating remediation workflow. It joins the exception register to customer claim coverage and ledger source fields, then assigns:

- evidence source and source-file reference,
- source-quality score,
- exception owner,
- remediation action,
- target resolution date,
- customer-claim impact,
- FMD impact,
- open/monitor status.

The purpose is to show what an analyst should do next. High-severity and material customer-impacting items stay visible as unresolved operating risks until the underlying evidence issue is corrected, replaced, or excluded from the claim. The register is not legal advice or compliance sign-off.

The control engine creates an exception register and a contract summary. The contract summary calculates eligible matched MWh, ineligible allocated MWh, shortfall, surplus, assumed replacement price, and estimated exposure.

## What The Project Does Not Claim

The project does not provide trading advice, legal advice, compliance sign-off, live carbon prices, or real REGO inventory. It demonstrates an analyst workflow and control framework using transparent public, curated, and representative demo data.
