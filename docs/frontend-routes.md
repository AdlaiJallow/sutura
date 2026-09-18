# Sutura — Frontend Route Structure (Phase 1 Discovery)

Next.js App Router routes from spec §32, expanded with what each route needs from
`api-contract.md` and which components are shared to avoid the "duplicate forms and calculation
UI" trap §32 warns about. This is web-first; the Flutter app (Phase 7) mirrors the same screens
against the same API, reusing no code but duplicating no financial logic either (§30/§48-4) —
Flutter renders values the backend computed, exactly like web.

## 1. Shared components (build once, reuse everywhere)

| Component | Used by | Purpose |
|---|---|---|
| `PeriodSelector` | global top nav, every data route | Drives the `financial_period_id` used by every query on the page; persists selection across navigation |
| `MoneyEntryForm` | `/salary`, `/allowances`, `/income`, `/expenses`, `/savings` | Generic amount + currency + date + notes form with per-record-type field slots (e.g. `payment_method` for expenses, `income_type` for income); the single place client-side validation and money-input formatting live, so no route hand-rolls its own decimal input |
| `AmountDisplay` | everywhere a monetary value is rendered | Renders a `Decimal`-as-string API value with the correct currency symbol/precision; the only place `Intl.NumberFormat`-equivalent logic lives, so no page ever does its own math on a displayed amount |
| `CategoryProgressBar` | `/dashboard`, `/distribution`, `/financial-periods/[id]` | Allocated / Used / Remaining / Overspent bar, fed by `GET /distributions/{period_id}` |
| `DataTable` | `/allowances`, `/income`, `/expenses`, `/transactions` | Paginated, filterable, sortable table wired to the API's pagination envelope (`data`/`meta`) |
| `ConfirmDialog` | delete actions, period close/reopen | Destructive-action confirmation, required by spec §33 ("confirm destructive actions") |
| `AttachmentUploader` | `/expenses` (expense detail/edit only) | Multipart upload widget against `POST /expenses/{id}/attachments`; not reused elsewhere since attachments are expense-scoped (D-005) |
| `StatusBadge` | `/financial-periods`, `/financial-periods/[id]`, `/expenses` | Renders Open/Closed/Modified, Recurring, Overspent states consistently |
| `ChartCard` | `/dashboard`, `/analytics` | Wraps Recharts with the app's consistent axis/legend/tooltip styling |
| `RuleEditor` | `/distribution`, `/savings` (savings-distribution-rules) | Percentage-list editor with live "sum = 100%" validation feedback, shared because both `DistributionRule` and `SavingsDistributionRule` need identical UX (add row, delete row, running total, reject save if ≠ 100%) |

## 2. Routes

### `/`
Landing/redirect: authenticated → `/dashboard`, unauthenticated → `/login`. No API calls of its own.

### `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`
Auth flows against `/api/v1/auth/*`. No shared components beyond basic form primitives (not
finance-specific, out of scope for this list).

### `/dashboard`
Needs (all for the currently-selected period via `PeriodSelector`):
- `GET /financial-periods/{id}/summary` — income, distribution, spending, savings, account
  sections (§21) in one call rather than one call per widget, since this is the highest-traffic
  page and §44 asks for fast dashboard loading.
- `GET /distributions/{period_id}` — category cards.
- `GET /bank-accounts` — current balances.

Shared components: `CategoryProgressBar`, `ChartCard`, `AmountDisplay`, `StatusBadge`.

### `/financial-periods`
List of periods. Needs: `GET /financial-periods` (paginated). Row actions: open a period, see
Open/Closed status (`StatusBadge`).

### `/financial-periods/[id]`
The full period drill-down (§23), tabbed: Overview / Income / Expenses / Distribution / Savings /
Accounts. Needs:
- `GET /financial-periods/{id}`
- `GET /financial-periods/{id}/summary`
- Per-tab: the same endpoints as the dedicated `/income`, `/expenses`, etc. routes below, scoped
  to this `financial_period_id` — **this is exactly why those endpoints take a
  `financial_period_id` filter rather than being period-nested-only**: the same `DataTable` +
  API call is reused here and on the standalone list routes, so the forms/tables are never
  duplicated (§32).
- Close/Reopen actions: `POST /financial-periods/{id}/close` / `/reopen` behind `ConfirmDialog`.
- Rule selection: `POST /financial-periods/{id}/select-distribution-rule`.

### `/salary`
Needs: `GET /salaries?financial_period_id=`, `POST /salaries`. Uses `MoneyEntryForm` (salary
variant: net_amount, currency, status, notes — no category field). Enforces one-per-period client-side
too (immediate validation per §33) but the real enforcement is server-side (409, D-008).

### `/allowances`
Needs: `GET /allowances?financial_period_id=`, CRUD. Uses `MoneyEntryForm` (allowance variant: name
from suggested list + "Other", amount, recurring toggle, date), `DataTable`.

### `/income`
Needs: `GET /income?financial_period_id=`, CRUD. Uses `MoneyEntryForm` (income variant:
`income_type` dropdown excluding Salary/Allowance per D-007, description, source, recurring
toggle), `DataTable`.

### `/expenses`
Needs: `GET /expenses?financial_period_id=`, CRUD, `AttachmentUploader`. Uses `MoneyEntryForm`
(expense variant: name, `expense_category`, `distribution_category_id` selector — populated from
the period's active `DistributionRule` categories — amount, payment_method, bank_account_id,
date), `DataTable`, `StatusBadge` (overspent indicator per row's category).

### `/distribution`
Needs:
- `GET /distribution-rules` (manage rules) — `RuleEditor` for create/edit with live 100%
  validation (D-009).
- `GET /distributions/{period_id}` — the allocated/used/remaining view for the selected period,
  reusing `CategoryProgressBar` (same component as `/dashboard`, not a re-implementation).
- `GET /distributions/{period_id}/categories/{category_id}/items` when a user drills into a
  category — this renders the same `Expense` rows as `/expenses` filtered by category, via the
  same `DataTable`, not a parallel "distribution item" table/UI (D-006 — there is no
  DistributionItem to render separately).

### `/savings`
Needs:
- `GET /savings/{period_id}` — automatic/manual/final/distributed/undistributed rollup.
- `GET /savings-items`, CRUD via `MoneyEntryForm` (savings-item variant: name, amount, date,
  destination).
- `GET /savings-distribution-rules`, CRUD via the shared `RuleEditor` (same component as
  `/distribution`'s rule editor — percentage list, live sum validation).
- `GET /savings-allocations?financial_period_id=`, `POST /savings-allocations`,
  `POST /savings-allocations/apply-rule` — manual or rule-driven distribution to accounts, with
  inline validation against `undistributed_total` before submit (mirrors the server-side 409 the
  API would otherwise return, per §33 "prevent invalid financial states").

### `/bank-accounts`
Needs: `GET /bank-accounts`, CRUD. Displays masked identifiers only (server never returns the full
value, D-011/§17); no client-side unmasking exists in v1.

### `/transactions`
Needs: `GET /bank-transactions?bank_account_id=&financial_period_id=`, `DataTable`,
`POST /bank-transactions` (manual deposit/withdrawal/adjustment), `POST /bank-transactions/transfer`
(a dedicated two-account form, not `MoneyEntryForm`, since a transfer inherently needs two account
fields). No edit/delete UI at all — the ledger is append-only (D-016); the UI surfaces "add
adjustment" as the correction path instead of an edit button.

### `/reports`
Needs: the `GET /reports/*` family plus `POST /reports/{report_type}/export` +
`GET /reports/exports/{job_id}` polling for PDF/CSV/XLSX downloads (§42). Uses `ChartCard` and
`DataTable` for on-screen views; export is a background job per §44 ("background report generation
when expensive").

### `/analytics`
Needs: the `GET /analytics/*` family (§24). Exclusively `ChartCard` components (trend lines, bar
charts for spending-by-category, etc.) — no forms on this route at all.

### `/settings`
Needs: `GET/PATCH /users/me`, `POST /users/me/change-password`, MFA enable/verify, default currency
selection (feeds every new `MoneyEntryForm`'s default currency, per D-002).

## 3. Why filters-on-flat-routes instead of period-nested routes

Every list endpoint (`/expenses`, `/income`, `/allowances`, `/bank-transactions`, ...) takes
`financial_period_id` as a **query filter**, not as a required path segment
(`/financial-periods/{id}/expenses`). This is deliberate: it lets `/financial-periods/[id]`'s tabs
and the standalone `/expenses`, `/income`, etc. routes call the *exact same* endpoint with the
*exact same* `DataTable`/`MoneyEntryForm` components, differing only in whether `PeriodSelector`'s
current value or the route's `[id]` param supplies the filter. Nesting the routes would force two
different data-fetching paths for what is otherwise identical UI — precisely the duplication §32
warns against.
