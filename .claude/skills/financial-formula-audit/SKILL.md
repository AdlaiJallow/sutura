---
name: financial-formula-audit
description: Audit financial calculation code (income totals, distribution allocation, category remaining, automatic/final savings, bank allocation, monthly summary) against the canonical formulas and rules in CLAUDE.md and spec §11-15/§26-27/§40. Use before merging any change to the financial_engine or any code that computes a monetary value, and whenever asked to "check the math", "audit the calculations", or "verify the formulas".
---

# Financial Formula Audit

Use this skill to verify that financial calculation code in Sutura is correct, uses exact arithmetic, and matches the spec — not to write new features.

## Procedure

1. **Locate every formula site.** Grep for the calculators this touches (income, distribution, expense, savings, bank-allocation, monthly-summary) under the financial engine module. List every function that computes a monetary value.

2. **Check arithmetic type.** Every monetary computation must use `Decimal` in Python (never `float`, never plain `int` division). In the DB layer, every monetary column must be `NUMERIC`/`DECIMAL`. Flag any `float`, `//`, or implicit int/float coercion touching money.

3. **Check each formula against the canonical set** (from CLAUDE.md / spec §26):
   ```
   Total Allowances       = SUM(Allowances)
   Total Salary Income     = Net Salary + Total Allowances
   Total Monthly Income     = Total Salary Income + Other Income
   Category Allocation     = Total Monthly Income × Category Percentage
   Category Used           = SUM(Category Items)
   Category Remaining      = Category Allocation - Category Used
   Automatic Savings       = SUM(Eligible Positive Category Remaining Values)
   Final Savings           = Automatic Savings + Manual Savings
   Undistributed Savings   = Final Savings - Savings Distributed
   ```
   For each, confirm the code matches term-for-term — not an approximation, not a formula that silently includes or excludes a term the spec doesn't mention.

4. **Check the configurable pieces aren't hardcoded**: which category types feed Automatic Savings must be data/config, not a hardcoded list of category names (spec §14). Distribution rule percentages must be validated to sum to exactly 100% (or explicit "Unallocated") before save (spec §10).

5. **Check the invariants that must never be silently violated**:
   - Overspending shows as a negative `Category Remaining`; it never auto-transfers from another category.
   - Savings distributed to accounts is validated `<= Final Savings` at write time — never allowed to silently over-allocate.
   - A closed `FinancialPeriod`'s stored summary is never recalculated without the explicit reopen flow + audit event.
   - No formula reads a client-submitted total as authoritative; every total is recomputed server-side from persisted records.

6. **Check test coverage.** Every formula above should have a unit test with `Decimal` inputs, including a rounding case and the full worked example from spec §40 (Net Salary D10,000 + D2,000 + D1,000 allowances + D500 + D500 other income → D14,000 total → 50/30/20 → D6,500/D3,900/D2,300 actual spend → D500/D300/D500 remaining → D1,300 automatic savings → D700/D400/D200 bank distribution → D0 undistributed). If this exact scenario isn't covered anywhere, that's a gap to report, not silently fix unless asked to.

## Output

Report as a list of findings: file:line, the formula or rule affected, what's wrong (or confirm it's correct), and the concrete input that would expose the bug if left unfixed. Don't rewrite the code unless asked — this skill's job is to audit and report.
