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

// NOTE: as of Phase 5 part 1, the backend has no `GET /distributions/{period_id}`
// (or equivalent) endpoint that returns per-category allocation/used/remaining for
// a period — only `/distribution-rules` CRUD (name + percentage only, no computed
// amounts). `DistributionView`/`DistributionCategorySummary` describe the shape such
// an endpoint would need to return (and what `CategoryProgressBar` already renders),
// kept here for the landing page's illustrative preview and for the real `/distribution`
// page once that backend endpoint exists. Flagged rather than invented — see the
// Phase 5 part 1 handback notes: this is a real gap, not a client-side shortcut.
export interface DistributionCategorySummary {
  id: string;
  name: string;
  percentage: Percentage;
  allocation: Money;
  used: Money;
  remaining: Money;
  is_overspent: boolean;
  contributes_to_automatic_savings: boolean;
  is_unallocated_bucket: boolean;
}

export interface DistributionView {
  financial_period_id: string;
  categories: DistributionCategorySummary[];
  total_allocation: Money;
  total_used: Money;
  total_remaining: Money;
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
