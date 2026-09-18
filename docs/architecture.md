# Sutura — Architecture (Phase 1 Discovery)

This document confirms and refines the modular-monolith architecture from spec §29, describes how
web and mobile share one backend, where `financial_engine` sits, and resolves every architecture- or
data-model-relevant ambiguity found in the spec. Full reasoning for each resolution lives in
[`decisions.md`](./decisions.md) (referenced inline as `D-0xx`); this document states the concrete
outcome.

## 1. Guiding principles (non-negotiable, from CLAUDE.md / spec §48)

- The backend is the sole source of truth for every number shown. No client ever submits a total that
  gets trusted (§46).
- `Decimal` in Python, `NUMERIC` in Postgres, everywhere money appears. No floats, ever (§26, D-019).
- Modular monolith, one FastAPI app, one Postgres database. No microservices (§4, §48-8).
- Financial calculations live in exactly one place (`financial_engine/`) and nowhere else — not in
  frontend components, not duplicated in Flutter (§30, §48-3/4).
- Every financial record is scoped to a `user_id`; ownership is enforced in the query itself, not as
  a post-fetch check (§34, D-015, D-020).
- Closed periods are never silently rewritten (§37, D-004).

## 2. High-level topology

```
                    ┌─────────────┐        ┌──────────────┐
                    │  Next.js    │        │   Flutter    │
                    │  Web        │        │   Mobile     │
                    └──────┬──────┘        └──────┬───────┘
                           │   REST /api/v1 (JSON)  │
                           └───────────┬────────────┘
                                       ▼
                          ┌─────────────────────────┐
                          │       FastAPI app        │
                          │  (single deployable)     │
                          │                          │
                          │  routes → schemas →      │
                          │  services → repositories │
                          │       → models           │
                          │                          │
                          │  financial_engine/ (pure │
                          │  Decimal calculators,    │
                          │  no I/O, no DB session)  │
                          └────────────┬─────────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
              ┌────────────┐   ┌──────────────┐   ┌─────────────┐
              │ PostgreSQL │   │ Redis+Celery │   │ S3-compat   │
              │ (NUMERIC)  │   │ (recurring,  │   │ storage     │
              │            │   │  reports,    │   │ (receipts)  │
              │            │   │  reconcile)  │   │             │
              └────────────┘   └──────────────┘   └─────────────┘
```

Both clients talk to the **same** versioned REST API. There is no client-specific backend, no
GraphQL gateway per client, no separate "mobile API." Web uses the browser session
(httpOnly refresh cookie + short-lived access token held in memory); Flutter uses the same JWT
issuance endpoints with the token stored in secure device storage. Every financial computation a
client displays was computed server-side and returned as-is; clients format/display, they never
recompute (§30, §46, §48-3/4).

## 3. Module map

FastAPI backend, one process, modules per spec §29:

```
backend/app/
├── auth/                # login, register, verification, reset, OAuth, MFA, session/JWT issuance
├── users/                # profile, default currency, account settings
├── financial_periods/    # FinancialPeriod CRUD, close/reopen, rule selection, RecurringTemplate
├── salary/                # Salary CRUD
├── allowances/            # Allowance CRUD
├── income/                # generic Income CRUD (excludes salary/allowance, D-007)
├── expenses/              # Expense CRUD, distribution_category linkage, attachments
├── distribution/          # DistributionRule, DistributionCategory, read-only "distributions" view
├── savings/                # Savings aggregate, SavingsItem, SavingsDistributionRule, SavingsAllocation
├── banks/                  # BankAccount CRUD, masking
├── transactions/            # BankTransaction (append-only ledger), transfers
├── reports/                # report generation (sync for small, Celery for exports)
├── analytics/              # trend/aggregate read endpoints across periods
├── attachments/            # S3 upload/download plumbing used by expenses
├── audit/                  # AuditLog write helper + read endpoints (admin/self only)
├── financial_engine/        # pure calculation layer — see §5 below
└── common/                  # base models, pagination, error envelope, DB session, security utils
```

Within each business module, four layers, always in this dependency direction:

```
routes (FastAPI routers, HTTP concerns only)
  → schemas (Pydantic request/response DTOs, validation)
    → services (business rules, orchestration, calls financial_engine, enforces ownership + period status)
      → repositories (SQLAlchemy queries, no business logic)
        → models (SQLAlchemy ORM models)
```

A route never touches a repository or model directly. A service never builds an HTTP response.
`financial_engine` never imports SQLAlchemy or FastAPI — it is pure functions over `Decimal` and
plain dataclasses/DTOs, callable and unit-testable with zero DB or web dependencies.

### Allowed dependency directions between modules

```
financial_periods ← salary, allowances, income, expenses, distribution, savings, transactions
                     (everything hangs off a period, §5)

distribution ← expenses (expense.distribution_category_id references distribution's tables)

salary, allowances, income → financial_engine.income_calculator
expenses, distribution     → financial_engine.distribution_calculator, expense_calculator
savings                    → financial_engine.savings_calculator
banks, transactions        → financial_engine.bank_allocation_calculator
financial_periods, reports → financial_engine.monthly_summary_calculator

auth, users  → no dependents besides "everything requires an authenticated user"
audit        ← every module that mutates a financial record (write-only dependency; audit never
               reads back into other modules' business logic)
attachments  ← expenses only (D-005)
```

`banks`/`transactions` never import from `distribution`/`expenses` directly for calculations —
they receive already-validated `Decimal` amounts and references from `savings`'s allocation flow.
This keeps the "financial event → budget allocation → actual expense → account transaction" chain
(§27) as one-directional references, never re-derivation.

## 4. financial_engine — where the math actually lives

```
financial_engine/
├── income_calculator.py       # total_allowances, total_salary_income, total_monthly_income
├── distribution_calculator.py # category_allocation, category_used, category_remaining, overspend
├── expense_calculator.py      # total_expenses, spending-by-category aggregation
├── savings_calculator.py      # automatic_savings (D-001 eligibility), final_savings, undistributed
├── bank_allocation_calculator.py # validates allocation <= available final savings, applies a
│                                   SavingsDistributionRule's percentages to a concrete amount
└── monthly_summary_calculator.py # assembles the full MonthlyFinancialSummary snapshot
```

Rules for this package:
- Every public function takes and returns `Decimal` (or DTOs composed of `Decimal`), never `float`.
- No function opens a DB session, calls another module's service, or performs I/O. Inputs are
  already-fetched `Decimal` values / lists of rows; outputs are `Decimal` results. This is what makes
  "independent unit tests reproducing the spec's worked examples" (§40, §49) possible without spinning
  up a database.
- Services (`distribution/services.py`, etc.) are the only callers. A service fetches persisted rows
  via its repository, calls the calculator, then persists any derived cache values (e.g. `Savings`
  aggregate, D-012) transactionally.
- Rounding: `Decimal` division for percentages uses `ROUND_HALF_UP` at 4 decimal places internally
  (matching the `NUMERIC(14,4)` column precision, D-019), then is presented rounded to the currency's
  display precision at the API/schema boundary — never rounded twice inconsistently.

## 5. How web and mobile share the backend

- One OpenAPI contract (`/api/v1`, FastAPI-generated) is the single interface both clients build
  against. Neither client has a "local" copy of any formula from §26 — every number is fetched, not
  computed, including intermediate values like "category remaining" and "final savings."
- Auth: same JWT issuance endpoints for both; web additionally uses an httpOnly refresh cookie (CSRF
  protection applies there), mobile uses secure on-device token storage with the same refresh flow.
- File uploads (receipts): both clients hit the same `attachments`-backed multipart endpoint; the
  backend validates type/size (§34) and writes to S3-compatible storage before either client sees a
  reference to it.
- Nothing about the module layout above is web- or mobile-specific. If a client-specific need arises
  (e.g. a mobile-optimized paginated response), it is a query-parameter variant of the same endpoint,
  not a parallel API.

## 6. Resolved ambiguities (concrete outcomes — see decisions.md for full reasoning)

| # | Topic | Resolution |
|---|-------|------------|
| D-001 | Automatic-savings eligibility | `DistributionCategory.contributes_to_automatic_savings BOOLEAN`, default `true`, user-editable per category. Only positive remainders from eligible categories are summed. |
| D-002 | Multi-currency readiness | Every money entity has `currency CHAR(3)`; `FinancialPeriod.base_currency` gates writes — mismatched currency in one period is rejected in v1 (no FX conversion yet), but no future migration needed to add it. |
| D-003 | Recurring generation | `RecurringTemplate` entity + Celery job materializes one concrete per-period row (`Salary`/`Allowance`/`Income`/`Expense`) per active template each period. Editing a template never touches past generated rows. |
| D-004 | Period close/reopen | Append-only `MonthlyFinancialSummary` versions (`is_current` flag), mandatory `reason` on reopen, `AuditLog` entry on both close and reopen, all child-record writes blocked while `status = CLOSED`. |
| D-005 | Attachments scope | `Attachment.expense_id` is a hard required FK — receipts only attach to expenses in v1, no polymorphic owner type. |
| D-006 | Expense vs. DistributionItem | Collapsed: no separate `DistributionItem` table. `Expense.distribution_category_id` is the link; `Category Used` = sum of expenses per category. `Expense.expense_category` is a second, independent column for the §9 suggested-category analytics dimension. |
| D-007 | Income taxonomy | `Income.income_type` excludes `SALARY`/`ALLOWANCE` (contradicts §8's literal list but follows §27's explicit double-counting rule and CLAUDE.md). |
| D-008 | Salary cardinality | Exactly one `Salary` row per user per period (`UNIQUE(user_id, financial_period_id)`). Extra payments go through `Income`. |
| D-009 | 100% validation | Enforced in the service layer inside a locked transaction, exact `100.00`, no epsilon — no DB trigger in v1. |
| D-010 | "Unallocated" category | `DistributionCategory.is_unallocated_bucket BOOLEAN`, not a name match. |
| D-011 | Bank balance derivation | Denormalized `current_balance`, recalculated transactionally on each `BankTransaction` insert, reconciled nightly by a Celery job against the full ledger sum. |
| D-012 | Savings entity design | `Savings` = per-period cached rollup (automatic/manual/final/distributed/undistributed), recalculated on every relevant change. `SavingsItem` = the only stored manual-entry source table. |
| D-013 | Savings distribution rules | New `SavingsDistributionRule` + `SavingsDistributionRuleItem` entities, structurally parallel to but distinct from income `DistributionRule`/`DistributionCategory`. |
| D-014 | Conceptual savings destinations | `SavingsAllocation.bank_account_id` nullable; `destination_label` covers non-account destinations like "Emergency Fund." Only real-account allocations generate a `BankTransaction`. |
| D-015 | Primary keys | UUIDv4 everywhere, defense in depth alongside mandatory ownership filtering. |
| D-016 | Delete semantics | Soft delete (`deleted_at`) for financial event tables; `BankTransaction` is fully append-only (corrections via `ADJUSTMENT` rows, never edited/deleted). |
| D-017 | Period granularity | Whole calendar month only (`year`, `month`), no arbitrary date ranges in v1. |
| D-018 | Concurrency | Optimistic check against `updated_at` on money-affecting writes; aggregates always recomputed from persisted rows, never trusted from the request. |
| D-019 | Column types | `NUMERIC(14,4)` for money, `NUMERIC(5,2)` for percentages. |
| D-020 | Cross-user access | 404, never 403, for records belonging to another user. |
| D-021 | API conventions | Offset pagination, resource-specific + universal filters, consistent error envelope (detailed in `api-contract.md`). |
| D-022 | Notifications/ML | Out of scope for the schema now; `AuditLog` + module boundaries leave room to add later without modifying existing modules. |

## 7. Explicit non-goals for this phase

- No microservices, no service mesh, no separate "calculation service" reachable over the network —
  `financial_engine` is an in-process Python package (§4, §48-8).
- No currency conversion logic (D-002).
- No notification delivery system (D-022).
- No ML/forecasting (§24 explicitly defers this until the core accounting model is stable).
- No code is scaffolded in this phase — Phase 2 (Foundation) builds the project skeleton against the
  contracts fixed by this document and `erd.md`/`api-contract.md`/`frontend-routes.md`.
