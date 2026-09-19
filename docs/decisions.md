# Architecture Decision Log

Canonical record of every non-obvious call made during Phase 1 (Discovery). Check here before
re-deciding something already settled. Each entry: **Decision / Context / Options considered / Why
this one**. Entries are numbered and immutable once written — a later change gets a new entry that
supersedes an old one explicitly (never edit history in place, same rule we apply to financial data).

Spec references are to `personal_finance_salary_distribution_ai_build_spec.md`.

---

### D-001: Automatic-savings eligibility is a per-category boolean, not a hardcoded category-name check

**Context:** Spec §14/§26 defines `Automatic Savings = SUM(Eligible Positive Category Remaining
Values)` but explicitly says eligibility "must be configurable rather than hidden in code" (§14).
Categories are user-named free text (e.g. "Needs", "Rent Bucket", "Chop Money") so eligibility can't
be inferred from a name.

**Options considered:**
1. Hardcode a list of category-name strings (e.g. "Needs", "Savings", "Wants") that count.
2. Infer eligibility from category `percentage` size or position.
3. Add a `contributes_to_automatic_savings BOOLEAN` column on `DistributionCategory`, user-editable,
   defaulting to `true`.

**Why this one:** Option 3 is the only one that satisfies the spec's explicit "configurable, not
hidden in code" requirement. Default `true` means the common case (all categories roll their unused
remainder into savings, matching the worked example in §14/§40) requires no user action; a user who
wants a category's leftovers to simply expire (e.g. a "Gifts" category they don't want inflating
savings) flips the flag off per category. Only **positive** remainders from eligible categories are
summed — negative remainders (overspend) are never subtracted from automatic savings, per the exact
wording of the formula ("Positive... Values").

---

### D-002: Multi-currency readiness = schema-ready, conversion-free; single currency enforced per period in v1

**Context:** Spec §25: support GMD now, design so multiple currencies can be added later, never
hardcode currency assumptions in business logic, but do not build FX conversion yet.

**Decision:** Every money-bearing entity carries its own `currency CHAR(3)` (ISO 4217) column,
defaulting to the user's `default_currency` (itself defaulting to `GMD`). `FinancialPeriod` carries a
`base_currency`. The service layer rejects any write whose `currency` differs from the owning
period's `base_currency` — there is no conversion table yet, so mixing currencies inside one period's
totals would silently produce meaningless sums. `financial_engine` never has a currency literal
baked into a formula; it operates on `(Decimal, currency)` pairs and only sums values that share a
currency.

**Options considered:** (a) no currency column at all, add later — rejected, would require a painful
backfill/migration and violates "design so multiple currencies can be supported later" now, not
later. (b) Build a currency-conversion/FX-rate table now — rejected as speculative complexity (rule
13); nothing in Phase 1–4 needs it. (c) Schema-ready + single-currency-per-period enforcement
(chosen) — gets the future-proofing without building unused conversion logic.

**Consequence:** Adding real multi-currency support later is an additive migration (an `ExchangeRate`
table + relaxing the per-period equality check + a "reporting currency" concept), not a schema
rewrite.

---

### D-003: Recurring records are generated from a `RecurringTemplate`, never by sharing a mutable row

**Context:** Spec §41 and CLAUDE.md are explicit: "a change in October must never rewrite September's
history." §28's suggested entity list has no template concept, only the concrete record types.

**Decision:** Introduce `RecurringTemplate` (not in the spec's suggested list, added per §28's
"final schema may be improved by the architect"). It stores the recurring definition (type, amount,
category, frequency, day-of-month, start/end period). A Celery job, run when a new `FinancialPeriod`
is created (and as a monthly scheduled sweep as a safety net), materializes one concrete `Salary` /
`Allowance` / `Income` / `Expense` row per active template for that period, stamping
`recurring_template_id` and `is_recurring_generated = true` on the generated row. Editing or
deactivating a template only changes what gets generated going forward; every already-generated row
is an independent, freely editable/deletable record that has no live link back to the template's
current values.

**Options considered:** (a) One mutable "recurring" row whose amount is read each period — rejected
outright, this is exactly the bug the spec warns against. (b) Cron duplicates the previous period's
row verbatim without a template — rejected: no single place to edit "my rent changed," and no
record of *why* a row was auto-created vs. manually entered. (c) Template + generated instances
(chosen) — matches how mature billing/subscription systems separate "the recurring intent" from
"the ledger entry."

**Note:** v1 supports `frequency = MONTHLY` only (documented explicitly, not silently); weekly/biweekly
recurrence is out of scope until requested (rule 13, no unused flexibility).

---

### D-004: Period close/reopen — append-only summary versions, no in-place rewrite

**Context:** Spec §37/§23: closed periods aren't casually edited; if editing is allowed, it needs an
explicit action, an audit event, a summary recalculation, and a visible "modified" indicator.

**Decision:**
- `FinancialPeriod.status` is `OPEN` or `CLOSED`.
- **Close**: allowed only when open. Computes a `MonthlyFinancialSummary` row with
  `version = 1, is_current = true, triggered_by = 'CLOSE'`, sets `closed_at`/`closed_by`, and writes
  an `AuditLog` entry (`action = 'CLOSE'`). While closed, all direct writes to the period's financial
  child records (`Salary`, `Allowance`, `Income`, `Expense`, `SavingsItem`, allocations) are rejected
  by the service layer with a 409, regardless of what the route layer does — ownership/period-status
  checks live in the service, not just the router (mirrors the ownership-check rule in CLAUDE.md).
- **Reopen**: requires a mandatory `reason` string, flips status back to `OPEN`, increments
  `reopened_count`, sets `last_reopened_at`, writes an `AuditLog` entry (`action = 'REOPEN'`,
  `before_state`/`after_state` capturing the summary snapshot being superseded).
- **Re-close after edits**: computes a *new* `MonthlyFinancialSummary` row
  (`version = previous + 1, is_current = true, triggered_by = 'REOPEN_RECALC'`) and flips the
  previous row's `is_current` to `false`. Old versions are never updated or deleted — the full
  history of "what did September look like at each point in time" stays queryable.
- The UI's "modified" indicator is simply `reopened_count > 0` (or `MAX(version) > 1`) on the period.

**Options considered:** (a) Update the single summary row in place on every recalculation — rejected,
loses the audit trail the spec insists on ("clearly indicate the period was modified" + full
auditability in §36). (b) A separate `PeriodRevision` snapshot table duplicating every child table —
rejected as heavy speculative complexity; the aggregate summary plus `AuditLog`'s before/after JSON
already gives full traceability of *what* changed, without duplicating every table. (c) Versioned
`MonthlyFinancialSummary` (chosen) — minimal new structure, directly satisfies the spec's wording.

---

### D-005: Attachments are scoped to `Expense` only in v1 — no polymorphic owner type yet

**Context:** Spec §9 mentions "optional receipt/document" only for expenses. §28 lists a generic
`Attachment` entity. Rule 13 (CLAUDE.md/spec §48-13): prefer simple solutions, no unused flexibility.

**Decision:** `Attachment.expense_id` is a required, non-nullable FK. No `owner_type`/`owner_id`
polymorphic pair. If a future phase needs attachments on bank transactions or income proof, that is
a new, explicit decision (and likely a new migration), not a pre-built generic slot sitting unused
today.

**Options considered:** (a) Polymorphic `owner_type` + `owner_id` now — rejected as speculative;
nothing in the spec asks for receipts anywhere but expenses, and a polymorphic FK can't be enforced
by the database the way a real FK can (referential integrity is weaker). (b) One `Attachment` table
per owning entity (e.g. `ExpenseAttachment`, future `IncomeAttachment`) — viable but premature since
only one is needed today. (c) Single table, hard FK to `Expense` (chosen).

---

### D-006: `DistributionItem` is not a separate ledger — it is `Expense.distribution_category_id`

**Context:** This is the most consequential ambiguity in the spec. §28 lists `DistributionItem` as
its own entity. §12 shows "items under distribution categories" (Rent, Food, Transport...) that look
identical in shape and amount to the `Expense` records described in §9 (which also has fields like
name, category, amount, date...). If both were modeled as separate money-holding tables, the same
real-world spend would be entered twice — directly contradicting §27's explicit warning: "an expense
recorded under a category must not be counted twice simply because it also appears as [another
record type]."

**Decision:** There is no separate `DistributionItem` table. Every `Expense` row carries a required
`distribution_category_id` FK (nullable only transiently, before a period has a distribution rule
selected). `Category Used` (§12) is computed as
`SUM(Expense.amount WHERE distribution_category_id = X AND deleted_at IS NULL)`. The spec's "items
under distribution categories" *are* expenses, viewed through a category lens — not a parallel
record type.

`Expense` keeps a **second**, independent categorization: `expense_category` (Rent, Food,
Transportation, Electricity, ... — the §9 suggested list), used for the "spending by category"
analytics in §24. This is intentionally a second column, not a reuse of `distribution_category_id`,
because the two taxonomies answer different questions ("which budget bucket did this draw down" vs.
"what kind of thing was this") and collapsing them would force a user's "Needs" bucket to also be
named "Rent," which breaks the moment a bucket contains more than one kind of spend (exactly the
§12 worked example: Rent + Food + Transport + Electricity all under one "Needs" category).

**Options considered:** (a) Keep `DistributionItem` as literally specified and let `Expense`
optionally reference it — rejected, creates exactly the double-ledger risk §27 warns about, and begs
the question of which row is authoritative for "actual spending." (b) Merge into `Expense` with two
category columns (chosen). (c) Merge into `Expense` with one category column, dropping the §9
suggested-category list — rejected, loses the §24 "spending by category" analytics dimension.

**This decision should be revisited only if** a future requirement needs a category item that is
*not* an actual cash expense (e.g. a pure "planned line item" with no real spend yet) — that would be
a genuinely different entity, not a rename of what exists today.

---

### D-007: `Income.income_type` excludes `SALARY` and `ALLOWANCE` despite §8's literal list

**Context:** §8 lists suggested income types including "Salary" and "Allowance" alongside "Per diem,"
"Freelance," etc. This directly contradicts §27 ("if a Housing Allowance is already included in the
salary/allowance calculation, it must not also be counted as separate Other Income") and CLAUDE.md's
explicit instruction that "the data model must clearly distinguish salary/allowance records from
generic income records."

**Decision:** Treat §27 and CLAUDE.md's explicit double-counting rule as authoritative over §8's
example list (which reads as illustrative of "kinds of money that come in," not a literal enum for
the `Income` table). `Income.income_type` enum = `IN_COUNTRY_PAYMENT, PER_DIEM, FREELANCE, BUSINESS,
INVESTMENT, OTHER`. Salary and allowances are only ever recorded through the dedicated `Salary` and
`Allowance` tables. This is flagged here explicitly per developer rule 1/2 (don't invent silently,
document the resolution) because it is a real contradiction in the source document, not a free
choice.

---

### D-008: One `Salary` row per user per `FinancialPeriod`

**Context:** §6 says "record their monthly net salary" (singular). Edge case §38-4 is "multiple
income payments in one month," which is a different concern (extra/other income, not multiple net
salary payments).

**Decision:** `UNIQUE(user_id, financial_period_id)` on `Salary`. If a user is genuinely paid more
than once in a calendar month from the same employer, the second payment is recorded via `Income`
with `income_type = OTHER` (or a future dedicated type) and a note — it does not create a second
`Salary` row. This keeps `Total Salary Income = Net Salary + Total Allowances` (§7) unambiguous: it
is always exactly one salary figure.

---

### D-009: Percentage totals must equal exactly 100.00, enforced in the service layer inside a DB transaction — not a Postgres trigger (yet)

**Context:** §10/§26: distribution rule percentages "must total exactly 100%" or include an explicit
"Unallocated" category; §20 says the same for savings-distribution rules.

**Decision:** `DistributionCategory.percentage` and `SavingsDistributionRuleItem.percentage` are
`NUMERIC(5,2)`. Validation ("do all sibling rows for this rule sum to exactly 100.00") happens in the
service layer, inside the same DB transaction that writes the category rows (using a row lock on the
parent rule to prevent a race between two concurrent category edits — see D-018 on concurrency). No
epsilon/rounding tolerance is applied: if percentages don't divide evenly, the user is expected to use
the explicit "Unallocated" bucket (D-010) to absorb the remainder, exactly as the spec proposes as the
escape hatch.

**Options considered:** (a) Postgres `CONSTRAINT TRIGGER` summing sibling rows — rejected for v1 as
more moving parts than needed while all writes go through one service layer (rule 13); revisit if a
future bulk-import or direct-SQL path bypasses the API. (b) Application-layer validation only, no
row lock — rejected, vulnerable to two concurrent requests both editing categories for the same rule
and each seeing a stale sum. (c) Service-layer validation + explicit row lock (chosen).

---

### D-010: "Unallocated" is a boolean flag on `DistributionCategory`, not a name-matching convention

**Context:** §10 offers "an explicit Unallocated category" as the alternative to requiring exactly
100%. If this were detected by matching the string "Unallocated," it would break for non-English
users or anyone who names it differently.

**Decision:** `DistributionCategory.is_unallocated_bucket BOOLEAN DEFAULT false`, with a partial
unique index ensuring at most one such category per rule. When present, this category behaves like
any other for allocation/used/remaining purposes, but the UI labels it distinctly and it is excluded
from `contributes_to_automatic_savings` by default (unallocated money sitting idle is not "savings"
until the user says so).

---

### D-011: `BankAccount.current_balance` is denormalized and transactionally recalculated, reconciled nightly

**Context:** §18: "Bank balances should be derived from a reliable transaction history where
practical." §44: fast dashboard loading is a design goal. Edge case §38-33: "account balance
mismatch."

**Decision:** `current_balance` is a cached column, never written to directly by any endpoint. It is
recalculated as `opening_balance + SUM(signed transaction effect)` inside the same DB transaction
that inserts a `BankTransaction` (so reads stay O(1) instead of summing the full ledger on every
dashboard load). A nightly Celery job independently recomputes the true sum from the ledger and
compares it to the cached value; a mismatch writes an `AuditLog` entry and surfaces a "balance needs
attention" flag rather than silently overwriting either number.

**Options considered:** (a) Always compute on read (`SUM` over `BankTransaction` every time) —
correct but doesn't scale with §44's "fast dashboard loading" goal once transaction history is long.
(b) Cache with periodic reconciliation (chosen) — matches "derived... where practical" without a
per-request full-table scan.

---

### D-012: `Savings` is a per-period cached aggregate; `SavingsItem` is the only source-of-truth savings table

**Context:** §28 lists both `Savings` and `SavingsItem` with no further definition. §15/§16 describe
manual savings entries (clearly `SavingsItem`) and a rollup of automatic + manual + distributed +
undistributed (§15's "Final Savings" table). Automatic savings itself is *derived* (sum of eligible
positive category remainders — D-001), not something a user directly enters.

**Decision:** `Savings` is a 1:1-with-`FinancialPeriod` cache row holding the current computed
rollup (`automatic_savings_computed`, `manual_savings_total`, `final_savings_total`,
`distributed_total`, `undistributed_total`, `last_calculated_at`). It is recalculated by
`financial_engine.savings_calculator` whenever an input changes (expense added/edited/deleted,
manual `SavingsItem` added, allocation made) — same "cache derived from source records, recalculated
transactionally" pattern as D-011, for the same dashboard-performance reason. `SavingsItem` holds the
actual manual entries (§16 fields). Automatic savings itself has no row of its own outside this cache
and the frozen `MonthlyFinancialSummary` snapshot taken at period close — it would otherwise be a
third place the same derived number could drift out of sync.

---

### D-013: Savings-to-account distribution rules are a distinct entity from income distribution rules

**Context:** §20 describes percentage-based rules for splitting *final savings* across bank
destinations (Bank A 40%, Bank B 30%...) — structurally similar to §10's income `DistributionRule`
but conceptually different (splits savings money among accounts, not income among budget categories).

**Decision:** Added `SavingsDistributionRule` + `SavingsDistributionRuleItem` (new entities beyond
§28's list, permitted by "the final schema may be improved by the architect"). Each item references
either a `BankAccount` or a free-text `destination_label` (for conceptual destinations like "Emergency
Fund" that aren't a real account) and a percentage; percentages must sum to 100.00 (same validation
approach as D-009).

---

### D-014: `SavingsAllocation.bank_account_id` is nullable; conceptual destinations are allowed

**Context:** §15's example includes "Emergency Fund D200" as an allocation destination alongside real
banks, with no indication an Emergency Fund must be a registered `BankAccount`.

**Decision:** `SavingsAllocation` requires *either* `bank_account_id` *or* `destination_label`, not
both null (DB `CHECK`). Only allocations with a real `bank_account_id` generate a corresponding
`BankTransaction` (a conceptual destination has no ledger to post to). This lets users track
"D200 earmarked for Emergency Fund" without forcing them to first create a bank account for every
savings goal, while still using real transaction-backed accounting wherever a real account exists
(§18).

---

### D-015: UUID primary keys everywhere

**Context:** CLAUDE.md/§34: "a user must never be able to reach another user's records by changing an
ID." Ownership checks (filtering every query by `user_id`) are the real defense and are mandatory
regardless of key type — but sequential integer IDs make enumeration/guessing trivial as an
additional attack surface, and expose row-count/growth-rate information in URLs and API responses.

**Decision:** Every table's primary key is a `UUID` (v4), generated application- or DB-side
(`gen_random_uuid()`). This is defense in depth, not a substitute for ownership checks, which every
service method still performs explicitly.

---

### D-016: Soft delete for financial event records; bank ledger is fully append-only

**Context:** Edge case §38-18 "deleted income"; §36 requires auditing deletions with before-state;
§18 implies a ledger model for bank transactions.

**Decision:** `Salary`, `Allowance`, `Income`, `Expense`, `SavingsItem` all carry a nullable
`deleted_at`. A "delete" sets this timestamp (and writes an `AuditLog` with the full before-state),
excluded from all sums via `WHERE deleted_at IS NULL`, but never physically removed — so a closed
period's history is never structurally altered even if something is later found to be wrong and
corrected via the reopen flow (D-004). Deleting is only permitted while the owning period is `OPEN`;
deleting a record that belongs to a `CLOSED` period requires reopening first.

`BankTransaction` is stricter still: no `deleted_at`, no `UPDATE` path at all. Corrections happen by
posting a new `ADJUSTMENT` transaction that references the one being corrected via
`related_record_id`. This matches how real bank/ledger systems avoid rewriting history and directly
serves §18's "transaction-based accounting rather than simply changing balances."

---

### D-017: `FinancialPeriod` granularity is a whole calendar month in v1, not an arbitrary date range

**Context:** §5 says a period "normally" represents one calendar month, leaving the door open to
other granularities, but gives no concrete alternative use case.

**Decision:** v1 models `FinancialPeriod` as `(user_id, year, month)` with a uniqueness constraint,
and derives `start_date`/`end_date` from that. No arbitrary custom-range periods. This is simpler to
reason about for recurring-record generation (D-003), period navigation, and analytics
month-over-month comparisons (§24), and nothing in the spec's worked examples needs anything finer or
coarser. If a real need for non-monthly periods emerges, it is a new decision, not a silently-assumed
capability sitting unused today (rule 13).

---

### D-018: Concurrency — optimistic locking via `updated_at`/version check on money-affecting writes

**Context:** Edge case §38-30 "concurrent updates." CLAUDE.md doesn't specify a mechanism.

**Decision:** Endpoints that mutate a record participating in a sum (`Expense`, `Allowance`,
`Income`, `DistributionCategory`, `SavingsAllocation`) require the client to send back the
`updated_at` value it last read (via an `If-Unmodified-Since`-style check enforced in the service
layer, not just relying on HTTP semantics); a stale write is rejected with 409 rather than silently
overwriting a concurrent change. Aggregate recalculation (Savings cache, category remaining) always
re-reads from persisted rows rather than trusting an in-memory total passed between requests — this
is the same principle as "never trust a client-submitted total" (§46) applied to server-side request
handling too.

---

### D-019: Money columns are `NUMERIC(14,4)`; percentages are `NUMERIC(5,2)`

**Context:** §25/§26: decimal arithmetic only, currency-ready for the future, GMD uses 2 decimal
places.

**Decision:** All monetary amounts are stored as `NUMERIC(14,4)` — two extra decimal places of
headroom beyond GMD's 2dp display convention, so a future currency that needs 3–4 decimal places
(some do) doesn't require a column migration; GMD amounts are simply always `.0000`-aligned to whole
cents in practice, and the presentation layer rounds to each currency's proper display precision.
Percentages are `NUMERIC(5,2)` (range 0.00–100.00). `Decimal` is used exclusively in Python; float
never appears in any code path that touches money, per rule 4.

---

### D-020: API error responses use 404 (not 403) for cross-user record access

**Context:** §34: never let a user reach another user's records by changing an ID.

**Decision:** When an authenticated user requests a record ID that exists but belongs to another
user, the API returns `404 Not Found`, identical to the response for a genuinely nonexistent ID —
never `403 Forbidden`. A 403 would confirm the record's existence, leaking information. Every
repository-layer query filters by the authenticated `user_id` as part of the `WHERE` clause itself
(not as a post-fetch check), so a cross-user record is architecturally indistinguishable from a
missing one.

---

### D-021: Pagination/filtering/sorting/error envelope conventions (applies to every list endpoint)

**Decision:** Offset-based pagination (`page`, `page_size`, max `page_size = 100`), response envelope
`{"data": [...], "meta": {"page", "page_size", "total_items", "total_pages"}}`; filtering via
resource-specific query params plus universal `date_from`/`date_to` and `financial_period_id` where
applicable; sorting via `sort_by`/`sort_dir`; errors as
`{"error": {"code", "message", "field_errors": [...]}}`. Chosen over cursor-based pagination for
simplicity (rule 13) — nothing in this app has the row-count or real-time-insert profile that
usually motivates cursors; revisit only if a specific list (e.g. bank transactions on a
years-old account) proves slow under offset pagination.

---

### D-022: Notifications and advanced analytics/ML are explicitly out of scope for the schema built now

**Context:** §43 says the architecture should be "future-ready" for notifications without making them
a core dependency; §24 explicitly defers ML/forecasting until the core accounting model is stable.

**Decision:** No `Notification` table or Celery notification tasks are built in Phase 1. The only
future-readiness commitment made now is that `AuditLog` and the module boundaries (`common/`) provide
enough of an event trail that a notification module could later subscribe to "important financial
changes" without modifying existing modules. No forecasting tables/columns are added anywhere.

---

### D-023: `Savings.undistributed_total` may go negative — the original `>= 0` CHECK contradicted this
codebase's own overspending philosophy and was removed

**Context:** Discovered during Phase 4 (Accounts) as a real bug, not a hypothetical: `Savings` had
`CheckConstraint("undistributed_total >= 0", name="ck_savings_undistributed_nonneg")` (D-012's
original migration). `Undistributed Savings = Final Savings - Savings Distributed` (§26) is computed
in `FinancialPeriodService._compute_summary` with no clamping — correctly, since spec §13/§34 and
D-006/D-001 establish throughout this codebase that a shortfall (overspending, in that case) is
*shown as a visible negative value*, never clamped to zero and never allowed to silently corrupt a
write. "Negative final savings" is explicitly spec edge case §38-35, not an exotic scenario: it
happens whenever a `SavingsAllocation` was made against a `final_savings_total` that later drops (a
backing manual `SavingsItem` gets edited down, or an automatic-savings-eligible category's remaining
shrinks because an expense was added after the allocation). Before this fix, that entirely normal
sequence of edits crashed the next summary recalculation with a raw `IntegrityError`/500 instead of
surfacing the shortfall.

**Decision:** Drop `ck_savings_undistributed_nonneg` (migration + model). `undistributed_total` now
persists exactly what the formula produces, including negative values, matching how `Category
Remaining` has never had an analogous floor. The API/UI treats a negative `undistributed_total` as a
visible warning state ("you've allocated more than your current final savings covers") — the same
treatment already used for overspent categories — not an error state and not something to hide.

**Options considered:** (a) Clamp `undistributed_total = max(final - distributed, 0)` in
`_compute_summary` — rejected: this actively hides a real discrepancy (money marked as distributed
that the user's current final savings can no longer actually cover), which is worse than the
overspending case this codebase otherwise goes out of its way to surface. (b) Drop the CHECK
constraint (chosen) — the formula was already correct; the constraint was the bug.

---

### D-024: `BankAccount.current_balance` may legitimately go negative — no insufficient-funds
block on withdrawals or transfers, by the same "show it, don't hide it" philosophy as D-023

**Context:** Raised as an informational note during the Phase 4 security review: nothing stops a
`WITHDRAWAL` or a transfer's source leg from taking `current_balance` below zero, and there was no
decision record for whether that's intentional. Spec §17/§18 don't state a rule either way.

**Decision:** Allowed, deliberately. This codebase already treats a shortfall as something to
surface, never something to silently prevent or clamp: negative `Category Remaining` (§13), negative
`undistributed_total` (D-023). A cash or mobile-money account genuinely can go negative in real life
(a fee posts, a mobile-money account is drawn down before the user notices) — Sutura's job is to show
the resulting negative balance accurately, the same way it shows an overspent category, not to pretend
the withdrawal never happened. If a future requirement wants a hard block (e.g. for a specific account
type that can't legally go negative), that's a new, explicit decision — not something to infer from
this one.

**Options considered:** (a) Reject a withdrawal/transfer that would take `current_balance` negative —
rejected as inconsistent with every other "show it" precedent in this codebase, and it would silently
assume every account type behaves like a strict-no-overdraft bank account. (b) Allow it and surface it
plainly (chosen).

---

### D-025: `BankAccount.current_balance` is recalculated under a row lock, not incrementally updated
— fixing a real lost-update bug found in the Phase 4 security review

**Context:** The Phase 4 security review (F-1) found that every balance-affecting write
(`BankTransactionService.create`, `.transfer`, `SavingsAllocationService.create`) fetched the account
via a plain `SELECT` (`BankAccountRepository.get_owned`, no `FOR UPDATE`) and then did
`account.current_balance = Decimal(account.current_balance) + signed_amount` — a Python
read-modify-write with no lock. Under Postgres's default READ COMMITTED isolation, two concurrent
writes to the same account race: both read the same starting balance, and the second commit overwrites
the first's effect instead of accumulating it. This also deviated from D-011 as originally written,
which specified recalculating from `opening_balance + SUM(ledger)`, not incrementing a cached delta.

**Decision:** Every code path that mutates `current_balance` now locks the account row
(`SELECT ... FOR UPDATE`) before reading and updating it, closing the race directly — matching the
same pattern already used for `DistributionRule` (D-009) and `Savings` (D-014) row locks elsewhere in
this codebase. This is a targeted concurrency fix, not a redesign of D-011's reconciliation story; the
nightly ledger-sum reconciliation job D-011 describes is still future work and remains the
self-healing backstop for any drift that predates this fix.

**Options considered:** (a) Recompute `current_balance` from `SUM(bank_transactions)` on every write
(fully matching D-011's original wording) — more self-healing, but a larger change for what F-1
actually needs (correctness under concurrency, not drift-repair) and better suited to arriving
alongside the reconciliation job itself. (b) Row-lock the existing incremental update (chosen) — closes
the race with a minimal, already-established pattern; revisit if the reconciliation job later makes the
full recompute approach the natural place to consolidate this too.

---

### D-026: Refresh token delivered via httpOnly cookie, not the JSON response body — fixing a
real backend/architecture-doc mismatch found starting Phase 5

**Context:** `docs/architecture.md` §2/§5 states, as an already-made Phase 1 decision: "Web uses the
browser session (httpOnly refresh cookie + short-lived access token held in memory)... CSRF protection
applies there." The Phase 2 backend build never implemented this — `POST /auth/login` and
`POST /auth/refresh` return the refresh token as a plain field in the JSON body
(`TokenResponse(access_token=access, refresh_token=refresh)`, `app/auth/router.py`), and the frontend's
`lib/api.ts` had a comment referencing this exact architecture-doc section while never actually being
wired to receive a cookie, because the backend never sent one. Neither side was maliciously wrong; the
contract between them was simply never implemented, only commented.

**Decision:** Fix the backend to match the already-documented design, rather than downgrade the design
to match the easier-to-build code (same principle as D-023/D-025: the formula/architecture was right,
the implementation was the bug):
- `POST /auth/login` sets the refresh token via `Set-Cookie` (`httponly=True`, `samesite="lax"`,
  `secure=True` in production, `path=/api/v1/auth`) and returns only `access_token` in the JSON body.
- `POST /auth/refresh` reads the refresh token from that cookie (not a request body field), and
  **rotates** it — issues a new refresh token, revokes the old one, sets a new cookie — since the
  token-hash/revocation infrastructure already exists in `AuthRepository` and rotation is a real
  security improvement (limits the blast radius of a leaked refresh token to one use) for a small
  addition on top of work already being done here.
- `POST /auth/logout` reads the cookie, revokes that token server-side, and clears the cookie.
- CSRF: the access token travels only in an `Authorization: Bearer` header (never a cookie), which a
  cross-site request cannot forge; `/auth/refresh` is the one cookie-authenticated endpoint, and
  `SameSite=Lax` is the chosen defense for it rather than a double-submit CSRF token scheme (rule 13:
  simplest solution that actually closes the risk — `Lax` blocks the cross-site POST this endpoint
  would need to be attacked with).
- Frontend: the access token moves from `localStorage` to an in-memory holder (module-level variable or
  a React context, not persisted storage), matching architecture.md's "held in memory" wording. On app
  boot, a silent `credentials: "include"` call to `/auth/refresh` (the cookie goes automatically) mints
  a fresh access token before any protected page renders; if that call fails, the user is redirected to
  `/login`. This is also how "am I logged in" is determined — there is no separate persisted
  "is-authenticated" flag to go stale.

**Options considered:** (a) Keep both tokens in `localStorage`, drop the httpOnly-cookie plan — rejected:
this is strictly less secure (a refresh token in `localStorage` is readable by any successful XSS,
which is exactly what an httpOnly cookie is designed to prevent) and contradicts a decision already
made deliberately in Phase 1, not something to quietly abandon because the simpler path was already
half-built. (b) Implement the documented design properly (chosen).

---

### D-027 (flagged, not yet resolved): switching a period's distribution rule mid-period orphans
expenses tied to the old rule's categories from the category-breakdown view

**Context:** Found while building the `/distribution` page (Phase 5 part 3). `Expense.distribution_
category_id` references a specific `DistributionCategory`, which belongs to a specific
`DistributionRule`. `GET /distributions/{period_id}` (added this phase) only returns categories
belonging to the period's *currently selected* rule. If a user selects rule A, logs expenses against
its categories, then switches the period to rule B, those earlier expenses are still real rows with a
real `distribution_category_id` — but that category no longer appears in the view, so their spend
silently disappears from every category's "used" figure. `FinancialPeriodService._compute_summary`'s
period-wide `total_expenses` is unaffected (it sums all of the period's expenses regardless of
category), so the dashboard's top-line total stays correct — only the per-category breakdown becomes
incomplete. This is spec edge case §38-21 ("changed distribution rule"), which the spec flags as
needing explicit handling without prescribing what that handling is.

**Not resolved yet — options on the table:**
1. Block selecting a new rule for a period if the currently-selected rule's categories have any
   non-deleted expenses against them (force an explicit decision before switching, mirroring how
   `DistributionService.deactivate_rule`/`update_rule` already block deactivating a rule that's an open
   period's active selection).
2. On switching, null out `distribution_category_id` on the orphaned expenses (they'd then need
   `distribution_category_id: null`, which `ExpenseService._validate_distribution_category` currently
   only permits when *no* rule is selected at all — this option would need that rule loosened, or a
   distinct "uncategorized under the current rule" state added).
3. Have `GET /distributions/{period_id}` additionally report spend against categories *not* in the
   current rule as a separate "uncategorized / prior-rule spend" line, so nothing is silently dropped
   even though it can't be attributed to a current-rule category.

**Why this isn't fixed inline:** switching rules mid-period is not itself expected to be common (a
period normally picks one rule and uses it start to finish), and the three options above have real
trade-offs worth deciding deliberately rather than picking one under an unrelated task, per developer
rule 1/2 (flag ambiguity, don't invent silently). Revisit before/alongside whatever phase adds rule
history or period-level analytics that depend on category totals being complete.
