# REGO Control Framework

The REGO controls are designed to answer whether renewable certificate inventory can be evidenced cleanly against contract obligations and disclosure periods. Controls are implemented in `src/rego_controls.py`.

| Control ID | Description | Severity | Input fields | Logic | Business rationale | Suggested action |
| --- | --- | ---: | --- | --- | --- | --- |
| RC-001 | Missing certificate ID | High | certificate_id | Certificate ID is blank | Cannot evidence ownership or uniqueness | Obtain original certificate reference |
| RC-002 | Duplicate certificate ID | High | certificate_id | Same non-blank ID appears more than once | Double-counting risk | Investigate duplicates and remove double-counting |
| RC-003 | Retired but available | High | status, retired_date | Status is Available and retired_date exists | Inventory status error | Reconcile lifecycle status with registry evidence |
| RC-004 | Retirement before issue | High | issue_date, retired_date | retired_date is before issue_date | Impossible lifecycle | Correct date fields before use |
| RC-005 | Missing contract ID | Medium | status, allocated_date, contract_id | Allocated record lacks contract ID | Poor audit trail | Add contract reference or return to inventory |
| RC-006 | Invalid contract ID | High | contract_id | Contract ID not found in contract file | Allocation cannot be reconciled | Update contract master or correct allocation |
| RC-007 | Technology mismatch | Medium | technology, eligible_technology | Certificate technology does not match eligibility | Customer/product claim risk | Reallocate to eligible certificate batch |
| RC-008 | Country mismatch | Medium | country, eligible_country | Certificate country does not match eligibility | Disclosure eligibility risk | Replace with eligible country certificate |
| RC-009 | Vintage outside delivery period | High | generation_start, generation_end, delivery_period | Generation period falls outside contract delivery period | Contract non-compliance | Remove from coverage or source eligible vintage |
| RC-010 | Missing source file | Low | source_file | Source file is blank | Weak audit trail | Populate source lineage |
| RC-011 | Stale available certificate | Medium | status, last_updated | Available certificate older than freshness threshold | Process-control weakness | Refresh inventory status |
| RC-012 | Missing counterparty | Medium | counterparty, allocated_date | Allocated certificate lacks counterparty | Documentation weakness | Add counterparty from contract/allocation record |
| RC-013 | Retired without retirement date | High | status, retired_date | Status is Retired and retirement date is blank | Lifecycle data issue | Update retirement evidence |
| RC-014 | Available after allocation date inconsistency | Medium | status, allocated_date | Status is Available but allocation date exists | System-entry quality issue | Correct status/date fields |
| RC-015 | Contract shortfall | High | required_mwh, eligible_matched_mwh | Eligible MWh below required MWh | Procurement / delivery exposure | Source replacement REGOs or update allocation |

## Contract Coverage

For each contract, the engine calculates:

- Required MWh.
- Eligible matched REGO MWh.
- Ineligible allocated MWh.
- Shortfall or surplus.
- Assumed REGO replacement price.
- Estimated replacement exposure.

```text
Estimated replacement exposure = max(shortfall, 0) * assumed replacement price
```

Certificates are counted as eligible only when the contract exists, the certificate ID is valid and unique, the lifecycle/status fields are usable, technology and country match the contract, and generation dates fall inside the delivery period.
