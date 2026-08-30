# Analyst Note

## 1. Executive Summary

This monitor shows why carbon analysis for a renewables supplier is not limited to allowance prices. Auction data provides the compliance carbon-market signal, recent GB power-system data fetched at build time explains the physical emissions backdrop, and REGO reconciliation controls determine whether renewable supply claims can be evidenced against contracts and disclosure periods.

The generated dashboard is operational rather than purely market-facing. The carbon module shows UKA discount broadly stable over the comparison period 2024-10-03 to 2025-05-22. The auction demand signal is neutral. The NESO power pull was fetched at build time and shows carbon intensity below recent average, with the main driver classified as mixed generation effects. Those context signals matter, but the main action sits in the customer claim book: 2 representative customer/product claims are not supportable, 1 requires review, and 900 MWh is uncovered.

## 2. Carbon Market Signal

The carbon-market module uses official EEX EUA primary-auction data, manually curated ICE UKA auction inputs, and the official GOV.UK UK ETS Cost Containment Mechanism monthly price table rather than licensed live price feeds. UKA prices are denominated in GBP and EUA prices are denominated in EUR, so the pipeline converts EUA prices into GBP using the stated static EUR/GBP assumption before calculating spread.

The latest generated comparison shows UKA at GBP 33.8 and EUA at EUR 71.84, equivalent to GBP 61.78 using the stated FX assumption. The resulting UKA-EUA spread is GBP -27.98. This is a transparent auction-context indicator, not a live traded spread or a replacement for broker marks, exchange feeds, or internal trading data.

## 3. GB Power Fundamentals

The power-system module fetches recent data from the NESO Carbon Intensity API during the Python build. The dashboard compares the latest fetched carbon intensity of 88.0 g/kWh with a recent average of 110.5 g/kWh, and shows gas share, wind and solar share, low-carbon share, and scatter views linking generation mix to carbon intensity.

This matters because carbon-market commentary should be connected to physical system conditions. A higher-carbon generation mix may change the emissions context customers see, even though it is not the same thing as contractual renewable supply. Contractual renewable claims still depend on certificate ownership, eligibility, allocation, retirement, and disclosure evidence.

## 4. Customer Claim Coverage Findings

The claim coverage module is the commercial control layer. It reconciles representative customer/product claim contracts against eligible REGO evidence, contract coverage, excluded certificate volume, contract-scoped exceptions, and assumed replacement prices. Claim status is not affected by grid intensity or carbon prices; those are context layers only.

The customer claim coverage output shows 900 MWh uncovered, 652 MWh invalid or excluded, and GBP 6,412 of assumed cover-cost exposure. The primary not-supportable claims are driven by contract-scoped high-severity evidence issues and uncovered eligible volume.

The claim evidence register converts control exceptions into an operational remediation workflow. It contains 17 register items, including 16 open items, 15 customer-impacting items, and 14 FMD-impacting items. Each item carries an owner, status, target resolution date, source-evidence reference, impact label, and recommended remediation action.

The underlying REGO module remains the evidence engine. It reconciles representative demo certificate records against representative demo contracts for technology, country, generation vintage, lifecycle status, issue evidence, quantity fields, counterparty, source evidence, and contract ID validity. C-002 has a 750 MWh shortfall with GBP 5,438 estimated cover cost; C-001 has a 150 MWh shortfall with GBP 975 estimated cover cost. Total eligible REGO shortfall is 900 MWh, with GBP 6,412 of assumed replacement-cost exposure. 1 contract is covered or in surplus in the current generated output.

The exception register contains 12 high, 4 medium, and 1 low severity exceptions. It flags missing certificate IDs, duplicate IDs, invalid contract allocation, lifecycle errors, missing generation dates, missing issue dates, missing or invalid MWh quantities, technology mismatch, country mismatch, vintage mismatch, missing source file, stale available inventory, missing counterparty, retired certificates without retirement dates, and available certificates with allocation-date inconsistencies.

## 5. Operational Implications

The practical question is whether the supplier can evidence renewable delivery cleanly. The answer is mixed. The priority is to resolve high-severity certificate controls, replace ineligible or unsupported allocations, and source enough eligible certificates to cover open shortfalls before disclosure close.

The replacement-exposure calculation is deliberately simple: shortfall MWh multiplied by an assumed REGO replacement price in the contract file. It is not a market-price forecast, but it creates a clear pricing input for operational prioritisation.

The FMD layer adds disclosure-period context for 2024-25. It uses the GOV.UK FMD table to show a UK generation-average emissions factor of 154.0 gCO2/kWh and an FMD residual-mix context factor of 481.09 gCO2/kWh. These values are used only as reporting context for contracted and uncovered MWh; they do not validate the renewable claim and they are not official customer Scope 2 emissions.

The future Scope 2 readiness layer is a data-preparedness view, not a compliance result. It separates current annual REGO claim supportability from possible future expectations around hourly matching and deliverability. The current output classifies 0 contracts as high readiness, 1 as medium readiness, and 2 as low readiness. It does not apply final revised Scope 2 rules and it does not perform 24/7 matching.

The carbon-cost layer adds a market-cost lens without changing claim status. Using the latest generated UKA auction price of GBP 33.8 per tCO2, it converts selected emissions factors into indicative GBP/MWh values. For example, the FMD residual-mix context row is GBP 16.26 per MWh. This is not a bill calculation, power-price forecast, or REGO claim validation input.

## 6. Data Limitations

The carbon data are official public or manually curated inputs, not licensed live UKA/EUA market data. The UKA auction CSV is not an automated ICE feed and should be checked against ICE Report Centre before external analytical use. The carbon spread uses a stated static EUR/GBP assumption and should not be read as a live traded spread. GOV.UK CCM monthly averages are policy and market context, not auction clearing prices.

The power data are fetched from the NESO Carbon Intensity API at build time, served as static dashboard output, and may be revised by the source. The REGO ledger and contracts are representative demo operating data because certificate-level supplier allocations and customer contract mappings are not public datasets. Source controls currently report 0 warnings across 9 registered sources. Assumed replacement prices are illustrative. The monitor is not trading advice, legal advice, or compliance sign-off.
