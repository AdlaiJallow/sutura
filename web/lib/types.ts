// Sutura API types — mirrors docs/api-contract.md and docs/erd.md exactly.
// Money and percentage fields are strings, never numbers (see api-contract.md §0
// "Money in requests/responses") so the frontend never round-trips them through
// float-losing JSON parsing, and never computes with them either (CLAUDE.md).

export type Money = string; // e.g. "45250.0000"
export type Percentage = string; // e.g. "30.00"
export type ISODate = string; // "YYYY-MM-DD"
export type ISODateTime = string;

export interface PageMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface Paginated<T> {
  data: T[];
  meta: PageMeta;
}

export interface FieldError {
  field: string;
  message: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    field_errors?: FieldError[];
  };
}

export type PeriodStatus = "OPEN" | "CLOSED";

export interface FinancialPeriod {
  id: string;
  year: number;
  month: number;
  start_date: ISODate;
  end_date: ISODate;
  status: PeriodStatus;
  distribution_rule_id: string | null;
  base_currency: string;
  closed_at: ISODateTime | null;
  closed_by: string | null;
  reopened_count: number;
  last_reopened_at: ISODateTime | null;
}

// GET /distributions/{period_id} — DistributionViewRead (Phase 5 part 3, shape confirmed
// live against the running backend). Read-only, server-computed: allocation/used/remaining
// per category plus period totals, derived from `financial_engine.distribution_calculator`
// and never re-derived client-side (spec §9/§26/§27, CLAUDE.md). A period with no
// distribution rule selected yet is a normal 200 — `distribution_rule_id`/`_name` are
// `null` and `categories` is `[]`, not an error — the UI must treat that as an empty
// state, not a failure.
export interface DistributionCategorySummary {
  id: string;
  name: string;
  percentage: Percentage;
  allocation: Money;
  used: Money;
  /** May be negative when the category is overspent — shown as-is, never clamped (spec §13/§38). */
  remaining: Money;
  is_overspent: boolean;
  contributes_to_automatic_savings: boolean;
  is_unallocated_bucket: boolean;
}

export interface DistributionView {
  financial_period_id: string;
  distribution_rule_id: string | null;
  distribution_rule_name: string | null;
  total_monthly_income: Money;
  categories: DistributionCategorySummary[];
  total_allocation: Money;
  total_used: Money;
  total_remaining: Money;
}

// GET/POST/PATCH /distribution-rules, PUT /distribution-rules/{id}/categories —
// DistributionRuleRead. A distinct resource from `DistributionView` above: this is the
// CRUD rule *definition* (name + percentage only) a user builds once and reuses across
// periods, never the computed per-period amounts (see the comment on `DistributionView`).
export interface DistributionRuleCategory {
  id: string;
  name: string;
  percentage: Percentage;
  contributes_to_automatic_savings: boolean;
  is_unallocated_bucket: boolean;
  display_order: number;
}

export interface DistributionRule {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  is_default: boolean;
  categories: DistributionRuleCategory[];
  updated_at: ISODateTime;
}

// GET /savings/{period_id} — the live, source-of-truth savings rollup (D-012).
export interface SavingsSummary {
  financial_period_id: string;
  automatic_savings_computed: Money;
  manual_savings_total: Money;
  final_savings_total: Money;
  distributed_total: Money;
  /** May be negative — a shortfall is shown, never clamped (D-023). */
  undistributed_total: Money;
  last_calculated_at: ISODateTime | null;
}

// GET /bank-accounts, GET /bank-accounts/{id} — BankAccountRead.
export interface BankAccountSummary {
  id: string;
  account_name: string;
  institution_name: string | null;
  account_type: string | null;
  /** Null when no identifier was ever recorded — never the full number (D-034/D-015 masking). */
  account_identifier_last4: string | null;
  currency: string;
  opening_balance: Money;
  current_balance: Money;
  is_active: boolean;
  updated_at: ISODateTime;
}

// GET /financial-periods/{id}/summary — MonthlySummaryRead. This is the cached
// `MonthlyFinancialSummary` row (D-004): live-recalculated ("MANUAL_REFRESH") while
// the period is OPEN, frozen at whatever it was when the period was last closed
// otherwise. Deliberately flat, matching the backend exactly — no nested
// income/distribution/spending breakdown exists at this endpoint (see the
// DistributionView note above for the gap that leaves).
export interface MonthlySummary {
  id: string;
  financial_period_id: string;
  version: number;
  is_current: boolean;
  total_salary_income: Money;
  total_allowances: Money;
  total_other_income: Money;
  total_monthly_income: Money;
  total_expenses: Money;
  total_planned_savings: Money;
  automatic_savings: Money;
  manual_savings: Money;
  final_savings: Money;
  total_bank_deposits: Money;
  undistributed_savings: Money;
  triggered_by: string;
  calculated_at: ISODateTime;
}

// Illustrative fixture shape for the anonymous landing page's ledger preview only
// (app/page.tsx) — not backed by any real endpoint, never fetched, never shown to a
// signed-in user. Kept separate from `MonthlySummary` (the real endpoint's shape) so
// the two are never confused.
export interface LandingPreviewSummary {
  income: {
    total_monthly_income: Money;
  };
}

export type ExpenseCategory =
  | "RENT"
  | "FOOD"
  | "TRANSPORTATION"
  | "ELECTRICITY"
  | "WATER"
  | "INTERNET"
  | "PHONE"
  | "EDUCATION"
  | "HEALTHCARE"
  | "FAMILY_SUPPORT"
  | "ENTERTAINMENT"
  | "SHOPPING"
  | "DEBT_REPAYMENT"
  | "OTHER";

export type PaymentMethod = "CASH" | "BANK_TRANSFER" | "CARD" | "MOBILE_MONEY" | "OTHER";

// POST /auth/register — RegisterResponse. Registration does not log the user in;
// they verify their email, then sign in separately.
export interface RegisterResult {
  id: string;
  email: string;
  is_email_verified: boolean;
}

// POST /auth/login, POST /auth/refresh (D-026). The refresh token never appears here —
// it travels only via the httpOnly `refresh_token` cookie.
export interface AuthTokens {
  access_token: string;
  token_type: string;
}

// GET /users/me — UserRead.
export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  default_currency: string;
  is_email_verified: boolean;
  mfa_enabled: boolean;
  is_active: boolean;
}

// GET /salaries, GET /salaries/{id} — SalaryRead. Exactly one per financial
// period (D-008); a second POST for the same period returns 409 CONFLICT.
export type SalaryStatus = "EXPECTED" | "RECEIVED";

export interface Salary {
  id: string;
  financial_period_id: string;
  net_amount: Money;
  currency: string;
  status: SalaryStatus;
  notes: string | null;
  is_recurring_generated: boolean;
  updated_at: ISODateTime;
}

// GET /allowances, GET /allowances/{id} — AllowanceRead. Unlimited entries per
// period (spec §7).
export interface Allowance {
  id: string;
  financial_period_id: string;
  name: string;
  amount: Money;
  currency: string;
  is_recurring: boolean;
  date_received: ISODate;
  notes: string | null;
  updated_at: ISODateTime;
}

// GET /income, GET /income/{id} — IncomeRead. Deliberately excludes
// salary/allowance income types (D-007). Unlimited entries per period (spec §8).
export type IncomeType =
  | "IN_COUNTRY_PAYMENT"
  | "PER_DIEM"
  | "FREELANCE"
  | "BUSINESS"
  | "INVESTMENT"
  | "OTHER";

export interface IncomeRecord {
  id: string;
  financial_period_id: string;
  income_type: IncomeType;
  description: string;
  amount: Money;
  currency: string;
  date_received: ISODate;
  source: string | null;
  is_recurring: boolean;
  notes: string | null;
  updated_at: ISODateTime;
}

// GET /expenses, GET /expenses/{id} — ExpenseRead.
export interface Expense {
  id: string;
  financial_period_id: string;
  distribution_category_id: string | null;
  name: string;
  expense_category: ExpenseCategory | string;
  amount: Money;
  currency: string;
  expense_date: ISODate;
  payment_method: PaymentMethod | string | null;
  bank_account_id: string | null;
  notes: string | null;
  updated_at: ISODateTime;
}
