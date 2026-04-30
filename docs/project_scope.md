# Project Scope

## Project Name

UK Carbon & REGO Market Operations Monitor

## Subtitle

A public-facing HTML dashboard powered by a Python signal and reconciliation engine.

## Core Idea

This project connects three operating questions:

1. What is the current UK/EU carbon-market backdrop?
2. What is happening physically on the GB power system, and how does that affect emissions context?
3. Can renewable certificate inventory be matched cleanly against contract obligations, disclosure periods, and audit requirements?

The REGO reconciliation and control engine is the operational core. Carbon and power sections provide market context, while certificate controls show whether renewable supply claims can be evidenced cleanly.

## MVP Scope

Included:

- Static public HTML dashboard.
- Python data pipeline.
- Carbon market signal module.
- GB power fundamentals module.
- Representative demo REGO contract reconciliation module.
- Source register and data-quality controls.
- Analyst note and GitHub-ready documentation.

Excluded from the MVP:

- Grid connection or curtailment module.
- CfD Clean Industry Bonus or SBTi supplier screener.
- Carbon hedge fund framing, carbon as an asset class, Sharpe ratios, or equity carbon premium analysis.
- Complex forecasting models.
- EU ETS firm-matching module.

## Build Stages

1. Stage 0: Project setup.
2. Stage 1: Representative demo REGO data.
3. Stage 2: REGO controls engine.
4. Stage 3: Source register and data-quality checks.
5. Stage 4: HTML dashboard skeleton.
6. Stage 5: Carbon market signals.
7. Stage 6: GB power fundamentals.
8. Stage 7: Executive summary integration.
9. Stage 8: Analyst note and public packaging.

## Design Principle

Every visual or metric must answer: what does the analyst need to know or do next?
