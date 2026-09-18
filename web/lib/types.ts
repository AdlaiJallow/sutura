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

export interface ApiEnvelope<T> {
  data: T;
  meta?: Record<string, unknown>;
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
  user_id: string;
  year: number;
  month: number;
  start_date: ISODate;
  end_date: ISODate;
  status: PeriodStatus;
  distribution_rule_id: string | null;
  base_currency: string;
  closed_at: ISODateTime | null;
  reopened_count: number;
  last_reopened_at: ISODateTime | null;
}

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

export interface SavingsSummary {
  financial_period_id: string;
  planned_savings: Money;
  automatic_savings: Money;
  manual_savings: Money;
  final_savings: Money;
  distributed_savings: Money;
  undistributed_savings: Money;
}

export interface BankAccountSummary {
  id: string;
  account_name: string;
  institution_name: string | null;
  account_type: string;
  account_identifier_last4: string;
  currency: string;
  current_balance: Money;
  is_active: boolean;
  deposits_this_period?: Money;
  savings_allocated_this_period?: Money;
}

export interface PeriodSummary {
  financial_period_id: string;
  income: {
    net_salary: Money;
    total_allowances: Money;
    other_income: Money;
    total_monthly_income: Money;
  };
  distribution: {
    needs_allocation: Money;
    savings_allocation: Money;
    wants_allocation: Money;
    custom_categories: { name: string; allocation: Money }[];
  };
  spending: {
    total_expenses: Money;
    spending_by_category: { category: string; amount: Money }[];
    planned_vs_actual: { planned: Money; actual: Money };
  };
  savings: SavingsSummary;
  accounts: {
    total_balance: Money;
    total_deposits_this_period: Money;
    total_savings_allocated: Money;
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

// POST /auth/login
export interface AuthTokens {
  access_token: string;
  token_type: string;
}

// GET /users/me — profile, default currency, MFA status.
export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  default_currency: string;
  mfa_enabled: boolean;
  email_verified: boolean;
}

export interface Expense {
  id: string;
  financial_period_id: string;
  distribution_category_id: string | null;
  distribution_category_name?: string;
  name: string;
  expense_category: ExpenseCategory;
  amount: Money;
  currency: string;
  expense_date: ISODate;
  payment_method: PaymentMethod | null;
  bank_account_id: string | null;
  notes: string | null;
  is_recurring: boolean;
}
