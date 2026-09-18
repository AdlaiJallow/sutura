// Realistic mock data shaped exactly like the real API contract (docs/api-contract.md,
// docs/erd.md). Every figure below is what the *backend* would compute — the dashboard
// never sums these itself (CLAUDE.md: no client-side financial computation). When the
// FastAPI backend is wired in, `lib/api.ts` calls replace these fixtures 1:1 — no
// component-level rewrite needed.
//
// Currency is GMD (Gambian Dalasi, base_currency default per erd.md FinancialPeriod)
// and names reflect a Banjul-based household, per the product's target market.

import type {
  BankAccountSummary,
  DistributionView,
  Expense,
  FinancialPeriod,
  PeriodSummary,
  UserProfile,
} from "./types";

// GET /users/me
export const mockUser: UserProfile = {
  id: "user-1",
  full_name: "Fatou Ceesay",
  email: "fatou.ceesay@example.gm",
  default_currency: "GMD",
  mfa_enabled: false,
  email_verified: true,
};

export const mockCurrentPeriod: FinancialPeriod = {
  id: "8f14e45f-ceea-4c9a-8f1e-000000000001",
  user_id: "user-1",
  year: 2026,
  month: 9,
  start_date: "2026-09-01",
  end_date: "2026-09-30",
  status: "OPEN",
  distribution_rule_id: "dr-1",
  base_currency: "GMD",
  closed_at: null,
  reopened_count: 0,
  last_reopened_at: null,
};

export const mockPastPeriods: FinancialPeriod[] = [
  {
    id: "8f14e45f-ceea-4c9a-8f1e-000000000000",
    user_id: "user-1",
    year: 2026,
    month: 8,
    start_date: "2026-08-01",
    end_date: "2026-08-31",
    status: "CLOSED",
    distribution_rule_id: "dr-1",
    base_currency: "GMD",
    closed_at: "2026-09-02T09:14:00Z",
    reopened_count: 0,
    last_reopened_at: null,
  },
  {
    id: "8f14e45f-ceea-4c9a-8f1e-0000000000ff",
    user_id: "user-1",
    year: 2026,
    month: 7,
    start_date: "2026-07-01",
    end_date: "2026-07-31",
    status: "CLOSED",
    distribution_rule_id: "dr-1",
    base_currency: "GMD",
    closed_at: "2026-08-01T10:02:00Z",
    reopened_count: 1,
    last_reopened_at: "2026-08-05T16:40:00Z",
  },
];

// GET /financial-periods/{id}/summary
export const mockPeriodSummary: PeriodSummary = {
  financial_period_id: mockCurrentPeriod.id,
  income: {
    net_salary: "38500.0000",
    total_allowances: "6200.0000",
    other_income: "2400.0000",
    total_monthly_income: "47100.0000",
  },
  distribution: {
    needs_allocation: "23550.0000",
    savings_allocation: "9420.0000",
    wants_allocation: "9420.0000",
    custom_categories: [{ name: "Family Support", allocation: "4710.0000" }],
  },
  spending: {
    total_expenses: "31280.5000",
    spending_by_category: [
      { category: "RENT", amount: "12000.0000" },
      { category: "FOOD", amount: "6840.5000" },
      { category: "TRANSPORTATION", amount: "3100.0000" },
      { category: "ELECTRICITY", amount: "1450.0000" },
      { category: "INTERNET", amount: "1200.0000" },
      { category: "FAMILY_SUPPORT", amount: "4200.0000" },
      { category: "ENTERTAINMENT", amount: "2490.0000" },
    ],
    planned_vs_actual: { planned: "37590.0000", actual: "31280.5000" },
  },
  savings: {
    financial_period_id: mockCurrentPeriod.id,
    planned_savings: "9420.0000",
    automatic_savings: "3140.5000",
    manual_savings: "1500.0000",
    final_savings: "4640.5000",
    distributed_savings: "3000.0000",
    undistributed_savings: "1640.5000",
  },
  accounts: {
    total_balance: "58230.7500",
    total_deposits_this_period: "7100.0000",
    total_savings_allocated: "3000.0000",
  },
};

// A second, edge-case period summary: zero income, nothing distributed yet —
// used by the dashboard empty/zero-state test and story.
export const mockZeroIncomePeriodSummary: PeriodSummary = {
  financial_period_id: "period-zero",
  income: {
    net_salary: "0.0000",
    total_allowances: "0.0000",
    other_income: "0.0000",
    total_monthly_income: "0.0000",
  },
  distribution: {
    needs_allocation: "0.0000",
    savings_allocation: "0.0000",
    wants_allocation: "0.0000",
    custom_categories: [],
  },
  spending: {
    total_expenses: "0.0000",
    spending_by_category: [],
    planned_vs_actual: { planned: "0.0000", actual: "0.0000" },
  },
  savings: {
    financial_period_id: "period-zero",
    planned_savings: "0.0000",
    automatic_savings: "0.0000",
    manual_savings: "0.0000",
    final_savings: "0.0000",
    distributed_savings: "0.0000",
    undistributed_savings: "0.0000",
  },
  accounts: {
    total_balance: "0.0000",
    total_deposits_this_period: "0.0000",
    total_savings_allocated: "0.0000",
  },
};

// GET /distributions/{period_id}
export const mockDistribution: DistributionView = {
  financial_period_id: mockCurrentPeriod.id,
  total_allocation: "47100.0000",
  total_used: "31280.5000",
  total_remaining: "15819.5000",
  categories: [
    {
      id: "cat-needs",
      name: "Needs",
      percentage: "50.00",
      allocation: "23550.0000",
      used: "24290.0000",
      remaining: "-740.0000",
      is_overspent: true,
      contributes_to_automatic_savings: false,
      is_unallocated_bucket: false,
    },
    {
      id: "cat-wants",
      name: "Wants",
      percentage: "20.00",
      allocation: "9420.0000",
      used: "4979.0000",
      remaining: "4441.0000",
      is_overspent: false,
      contributes_to_automatic_savings: true,
      is_unallocated_bucket: false,
    },
    {
      id: "cat-savings",
      name: "Savings",
      percentage: "20.00",
      allocation: "9420.0000",
      used: "0.0000",
      remaining: "9420.0000",
      is_overspent: false,
      contributes_to_automatic_savings: true,
      is_unallocated_bucket: false,
    },
    {
      id: "cat-family",
      name: "Family Support",
      percentage: "10.00",
      allocation: "4710.0000",
      used: "2011.5000",
      remaining: "2698.5000",
      is_overspent: false,
      contributes_to_automatic_savings: true,
      is_unallocated_bucket: false,
    },
  ],
};

// GET /distributions/{period_id} for the zero-income period — no allocations exist
// because there is nothing to distribute yet (edge case: zero income, spec §38).
export const mockZeroDistribution: DistributionView = {
  financial_period_id: "period-zero",
  total_allocation: "0.0000",
  total_used: "0.0000",
  total_remaining: "0.0000",
  categories: [],
};

// Every financial period this user has, newest first — GET /financial-periods.
export const mockAllPeriods: FinancialPeriod[] = [mockCurrentPeriod, ...mockPastPeriods];

// GET /bank-accounts
export const mockBankAccounts: BankAccountSummary[] = [
  {
    id: "bank-1",
    account_name: "Everyday Spending",
    institution_name: "Trust Bank Gambia",
    account_type: "BANK",
    account_identifier_last4: "4821",
    currency: "GMD",
    current_balance: "18420.7500",
    is_active: true,
    deposits_this_period: "38500.0000",
    savings_allocated_this_period: "1000.0000",
  },
  {
    id: "bank-2",
    account_name: "Qcell Wallet",
    institution_name: "Qcell Money",
    account_type: "MOBILE_MONEY",
    account_identifier_last4: "0092",
    currency: "GMD",
    current_balance: "3210.0000",
    is_active: true,
    deposits_this_period: "2400.0000",
    savings_allocated_this_period: "500.0000",
  },
  {
    id: "bank-3",
    account_name: "Emergency Fund",
    institution_name: "Reliance Financial Services",
    account_type: "SAVINGS",
    account_identifier_last4: "7734",
    currency: "GMD",
    current_balance: "36600.0000",
    is_active: true,
    deposits_this_period: "1500.0000",
    savings_allocated_this_period: "1500.0000",
  },
];

// GET /expenses?financial_period_id=
export const mockExpenses: Expense[] = [
  {
    id: "exp-1",
    financial_period_id: mockCurrentPeriod.id,
    distribution_category_id: "cat-needs",
    distribution_category_name: "Needs",
    name: "September rent — Bakau compound",
    expense_category: "RENT",
    amount: "12000.0000",
    currency: "GMD",
    expense_date: "2026-09-02",
    payment_method: "BANK_TRANSFER",
    bank_account_id: "bank-1",
    notes: "Paid to landlord, includes water",
    is_recurring: true,
  },
  {
    id: "exp-2",
    financial_period_id: mockCurrentPeriod.id,
    distribution_category_id: "cat-needs",
    distribution_category_name: "Needs",
    name: "Weekly market — Serrekunda",
    expense_category: "FOOD",
    amount: "1640.5000",
    currency: "GMD",
    expense_date: "2026-09-14",
    payment_method: "CASH",
    bank_account_id: null,
    notes: null,
    is_recurring: false,
  },
  {
    id: "exp-3",
    financial_period_id: mockCurrentPeriod.id,
    distribution_category_id: "cat-family",
    distribution_category_name: "Family Support",
    name: "Send to mother — Basse",
    expense_category: "FAMILY_SUPPORT",
    amount: "2011.5000",
    currency: "GMD",
    expense_date: "2026-09-10",
    payment_method: "MOBILE_MONEY",
    bank_account_id: "bank-2",
    notes: "Monthly support",
    is_recurring: true,
  },
  {
    id: "exp-4",
    financial_period_id: mockCurrentPeriod.id,
    distribution_category_id: "cat-needs",
    distribution_category_name: "Needs",
    name: "NAWEC electricity top-up",
    expense_category: "ELECTRICITY",
    amount: "1450.0000",
    currency: "GMD",
    expense_date: "2026-09-08",
    payment_method: "MOBILE_MONEY",
    bank_account_id: "bank-2",
    notes: null,
    is_recurring: false,
  },
  {
    id: "exp-5",
    financial_period_id: mockCurrentPeriod.id,
    distribution_category_id: "cat-wants",
    distribution_category_name: "Wants",
    name: "Dinner — Ocean Bay Hotel",
    expense_category: "ENTERTAINMENT",
    amount: "890.0000",
    currency: "GMD",
    expense_date: "2026-09-13",
    payment_method: "CARD",
    bank_account_id: "bank-1",
    notes: "Birthday dinner",
    is_recurring: false,
  },
];
