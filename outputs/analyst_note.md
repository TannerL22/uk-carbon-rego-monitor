# Analyst Note

## 1. Executive Summary

This monitor shows why carbon analysis for a renewables supplier is not limited to allowance prices. Auction data provides the compliance carbon market signal, GB power fundamentals explain the physical emissions backdrop, and REGO reconciliation controls determine whether renewable supply claims can be evidenced against contracts and disclosure periods.

The current dashboard signal is operational rather than purely market-facing. The UKA auction sample shows a wider GBP-normalised discount to EUA auction pricing than recent history, while the live NESO power pull provides the recent GB physical-emissions backdrop. Those conditions provide useful context, but the main action sits in the certificate book: the representative demo REGO ledger contains 18 control exceptions, including 11 high-severity items, and two contracts have eligible certificate shortfalls.

## 2. Carbon Market Signal

The carbon-market module uses curated public-sample UKA and EUA auction results rather than licensed live price feeds. UKA prices are denominated in GBP and EUA prices are denominated in EUR, so the pipeline converts EUA prices into GBP using a stated EUR/GBP assumption before calculating spread. The latest sample shows UKA clearing prices below EUA clearing prices on that GBP-normalised basis, with the UKA-EUA spread wider than its trailing average. This is treated as a market-context signal, not as a trading recommendation. The auction demand signal is neutral because the latest UKA cover ratio is close to the recent average.

This approach is intentionally conservative. Public auction data can show direction, regime, and primary-market tone, but it cannot replace a live exchange feed, broker marks, FX-adjusted spread modelling, or internal trading data.

## 3. GB Power Fundamentals

The power-system module fetches recent live data from the NESO Carbon Intensity API during the Python build. The dashboard compares latest carbon intensity with the recent API window average and shows gas share, wind and solar share, low-carbon share, and scatter views linking generation mix to carbon intensity.

This matters because carbon-market commentary should be connected to physical system conditions. A higher-carbon generation mix may change the emissions context customers see, even though it is not the same thing as contractual renewable supply.

## 4. REGO Reconciliation Findings

The REGO module is the core control layer. It reconciles representative demo certificate records against representative demo contracts for technology, country, generation vintage, lifecycle status, counterparty, source evidence, and contract ID validity.

Contract C-002 has a 750 MWh eligible REGO shortfall against an 8,000 MWh solar-backed obligation. At the assumed replacement price of GBP 7.25/MWh, the estimated cover cost is GBP 5,438. Contract C-001 has a smaller 150 MWh shortfall, with an estimated exposure of GBP 975. Contract C-003 is covered, with 20,900 eligible matched MWh against a 20,000 MWh obligation.

The exception register flags missing certificate IDs, duplicate IDs, invalid contract allocation, lifecycle errors, technology mismatch, country mismatch, vintage mismatch, missing source file, stale available inventory, missing counterparty, retired certificates without retirement dates, and available certificates with allocation-date inconsistencies.

## 5. Operational Implications

The practical question is whether the supplier can evidence renewable delivery cleanly. The answer is mixed. There is enough eligible inventory for the FMD pool, but two customer contracts need action before close. The priority is to resolve high-severity certificate controls, replace ineligible or unsupported allocations, and source enough eligible certificates to cover the C-002 and C-001 shortfalls.

The replacement-exposure calculation is deliberately simple: shortfall MWh multiplied by an assumed REGO replacement price in the contract file. It is not a market-price forecast, but it creates a clear pricing input for operational prioritisation.

## 6. Data Limitations

The carbon data are public or curated auction samples, not licensed live UKA/EUA market data. The carbon spread uses a stated static EUR/GBP assumption and should not be read as a live traded spread. The power data are fetched live from the NESO Carbon Intensity API at build time and may be revised by the source. The REGO ledger and contracts are representative demo operating data because certificate-level supplier allocations and customer contract mappings are not public datasets. Assumed replacement prices are illustrative. The monitor is not trading advice, legal advice, or compliance sign-off.
