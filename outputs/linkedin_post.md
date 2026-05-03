Carbon analysis is not just watching allowance prices.

For a renewables supplier, it also means understanding power-system fundamentals, renewable certificate evidence, contract delivery periods, and inventory controls.

I built a small UK Carbon & REGO Market Operations Monitor to connect those pieces.

The workflow includes:
- UKA/EUA auction-based carbon market signals
- GOV.UK UK ETS CCM monthly price and trigger context
- GB carbon intensity and generation mix analysis
- A representative demo supplier-style REGO certificate ledger
- Contract-matching and certificate reconciliation controls
- Exception flags for duplicate IDs, lifecycle errors, vintage mismatches, technology mismatches, and certificate shortfalls
- A source register to track data limitations and update status

The goal was not to build a trading terminal. It was to build a practical analyst workflow: market intelligence, certificate controls, and documented assumptions.

I used AI-assisted coding tools to accelerate the build, but manually reviewed the business logic, control framework, and outputs.

GitHub: https://github.com/TannerL22/uk-carbon-rego-monitor
