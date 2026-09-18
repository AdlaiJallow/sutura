---
name: edge-case-audit
description: Check a feature, PR, or module against the 35 documented edge cases for the personal finance app (spec §38) - zero/no income, overspending, bank over-allocation, closed-period edits, rounding, concurrent updates, etc. - and report which are handled, which are gapped, and which are irrelevant to this feature. Use before considering any financial feature complete, or when asked to "check edge cases".
---

# Edge Case Audit

Sutura's spec (§38) lists 35 edge cases that must be explicitly designed for and tested. This skill checks a given feature/change against the ones that apply to it — it does not implement fixes itself unless asked to.

## The 35 cases (spec §38)

1. Salary with no allowances
2. Allowances with no other income
3. Other income with no salary
4. Multiple income payments in one month
5. Multiple allowances
6. No income
7. Zero income
8. Zero expenses
9. Category with no items
10. Entire category unused
11. Category overspending
12. Savings category fully unused
13. Manual savings without automatic savings
14. Partial bank allocation
15. Attempted bank over-allocation
16. Multiple bank accounts
17. Transfers between accounts
18. Deleted income
19. Edited income
20. Edited expense
21. Changed distribution rule
22. Additional income after distribution
23. Recurring income
24. Recurring expenses
25. Different currencies in future
26. Closed financial period
27. Duplicate transactions
28. Decimal rounding
29. Very large amounts
30. Concurrent updates
31. Failed bank allocation
32. Deleted/inactive bank account
33. Account balance mismatch
34. Negative category remaining
35. Negative final savings

## Procedure

1. Identify the feature/module under audit and read its code (service layer, API routes, and existing tests).
2. Filter the 35 cases to the ones actually relevant to this feature — don't force-fit irrelevant cases (e.g. "bank over-allocation" doesn't apply to an allowances CRUD endpoint), but be conservative: most changes touching income, expenses, distribution, or savings intersect several cases.
3. For each relevant case, determine: **Handled** (code + test both exist and behavior matches the spec's stated or recommended default), **Gapped** (behavior is undefined, untested, or contradicts the spec), or **Needs a decision** (the spec doesn't specify a default and none has been documented yet — e.g. spec explicitly leaves overspending's effect on other categories as something to define, with a recommended default in §13).
4. For every "Gapped" or "Needs a decision" item, state the concrete scenario that would currently break or behave surprisingly (input values, sequence of actions).

## Output

A table: case # / description / status (Handled / Gapped / Needs decision) / note. Follow with a short list of the highest-priority gaps to fix first — prioritize correctness-affecting gaps (rounding, overspending, over-allocation, closed-period edits) over cosmetic ones. Do not silently patch gaps unless explicitly asked to fix them after reporting.
