// Sutura API client — the ONLY place that talks to the FastAPI backend.
//
// Rules this file enforces for the rest of the app (see CLAUDE.md / frontend-engineer.md):
//   - Every monetary/derived figure comes back exactly as the API sent it (a string,
//     verified directly against the running backend — Decimal fields serialize as
//     strings, e.g. "45250.0000") — nothing here parses it into a float and nothing
//     upstream should either. Formatting happens only in <AmountDisplay />.
//   - Errors are surfaced in the documented error envelope shape, never swallowed.
//   - The base URL is always read from NEXT_PUBLIC_API_URL — never hardcoded.
//   - The access token lives ONLY in the module-level variable below — never in
//     localStorage/sessionStorage (D-026, architecture.md "held in memory"). The
//     refresh token is an httpOnly cookie the browser manages; this file never reads
//     or writes it directly.

import type { ApiErrorBody } from "./types";

const RAW_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, "");
const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;
  fieldErrors?: { field: string; message: string }[];

  constructor(status: number, body: ApiErrorBody) {
    super(body.error?.message ?? "Something went wrong. Please try again.");
    this.name = "ApiError";
    this.status = status;
    this.code = body.error?.code ?? "UNKNOWN_ERROR";
    this.fieldErrors = body.error?.field_errors;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE" | "PUT";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Optimistic-concurrency header for money-affecting PATCH/DELETE (D-018). */
  ifUnmodifiedSince?: string;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]) {
  const url = new URL(`${API_BASE_URL}${API_PREFIX}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

// --- In-memory access token holder (D-026) ---------------------------------------
// The single source of truth for "what access token does this tab currently have."
// Never persisted. Lost on a hard reload by design — `AuthProvider` (lib/auth-context.tsx)
// re-derives it on boot via a silent `POST /auth/refresh`, which reads the httpOnly
// refresh cookie the browser already carries.
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/**
 * Low-level typed fetch wrapper. Every domain call (see below) goes through this
 * so auth headers, the error envelope, and the base URL are handled in one place.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, ifUnmodifiedSince, signal } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (ifUnmodifiedSince) headers["If-Unmodified-Since"] = ifUnmodifiedSince;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      credentials: "include", // httpOnly refresh cookie, per architecture.md §5 / D-026
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch {
    throw new ApiError(0, {
      error: {
        code: "NETWORK_ERROR",
        message:
          "Couldn't reach the Sutura server. Check your connection and try again.",
      },
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const json = text ? JSON.parse(text) : undefined;

  if (!response.ok) {
    throw new ApiError(response.status, json as ApiErrorBody);
  }

  return json as T;
}

// ---------------------------------------------------------------------------
// Domain calls — thin, typed wrappers verified directly against the running
// backend (see Phase 5 part 1 handback notes). Every single-resource endpoint
// (GET /{id}, POST create, PATCH update, action endpoints) returns the resource
// directly — NOT wrapped in `{ data: ... }`. Only LIST endpoints use the
// `{ data: [...], meta: {...} }` envelope (`Paginated<T>`).
//
// Add new calls here as pages need them; never fetch() directly from a component.
// ---------------------------------------------------------------------------

import type {
  Allowance,
  AuthTokens,
  BankAccountSummary,
  BankAccountType,
  BankTransaction,
  BankTransactionType,
  BankTransferResult,
  DistributionRule,
  DistributionView,
  Expense,
  ExpenseCategory,
  FinancialPeriod,
  IncomeRecord,
  IncomeType,
  MonthlySummary,
  Paginated,
  PaymentMethod,
  RegisterResult,
  Salary,
  SalaryStatus,
  SavingsAllocation,
  SavingsDistributionRule,
  SavingsItem,
  SavingsSummary,
  UserProfile,
} from "./types";

/** Shared shape for a savings-distribution-rule item, whether creating a rule
 * (`POST /savings-distribution-rules`) or replacing its items (`PUT
 * /savings-distribution-rules/{id}/items`, where `id` marks an existing row to
 * update in place — omitted for a new one). Exactly one of `bank_account_id` /
 * `destination_label` must be set, mirroring the backend's `_require_destination`
 * validator — enforced server-side, this type just shapes the payload. */
export interface SavingsDistributionRuleItemInput {
  id?: string;
  bank_account_id?: string | null;
  destination_label?: string | null;
  percentage: string;
}

/** Shared shape for a distribution category row sent to the backend, whether
 * creating a rule (`POST /distribution-rules`) or replacing its categories
 * (`PUT /distribution-rules/{id}/categories`, where `id` marks an existing row
 * to update in place — omitted for a new one). Percentages are raw strings the
 * user typed, never `Number(...)`-round-tripped (same rule as every other
 * money/percentage field in this file). */
export interface DistributionCategoryInput {
  id?: string;
  name: string;
  percentage: string;
  contributes_to_automatic_savings?: boolean;
  is_unallocated_bucket?: boolean;
  display_order?: number;
}

export const api = {
  auth: {
    register: (body: { email: string; password: string; full_name: string }) =>
      apiFetch<RegisterResult>("/auth/register", { method: "POST", body }),
    login: (body: { email: string; password: string }) =>
      apiFetch<AuthTokens>("/auth/login", { method: "POST", body }),
    /** Reads the httpOnly refresh cookie automatically (`credentials: "include"`
     * above); rotates it server-side and mints a new access token. No request body. */
    refresh: () => apiFetch<AuthTokens>("/auth/refresh", { method: "POST" }),
    /** Revokes the refresh cookie server-side. No request body. Callers should
     * clear the in-memory access token regardless of whether this succeeds. */
    logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
  },
  users: {
    me: () => apiFetch<UserProfile>("/users/me"),
    /** Partial update — either field may be omitted. No `expected_updated_at`
     * on this endpoint (confirmed live: a bare `{full_name}` or `{default_currency}`
     * PATCH with no lock field succeeds), unlike the money-affecting resources. */
    update: (body: { full_name?: string; default_currency?: string }) =>
      apiFetch<UserProfile>("/users/me", { method: "PATCH", body }),
    /** 204 on success. A wrong `current_password` is a 401 UNAUTHORIZED with no
     * `field_errors` (confirmed live) — the caller shows it as a plain-language
     * error next to the current-password field, not a generic banner. */
    changePassword: (body: { current_password: string; new_password: string }) =>
      apiFetch<void>("/users/me/change-password", { method: "POST", body }),
    /** Deactivates the account (never a hard delete — spec-consistent with
     * bank account "deactivate"). Confirmed live: the backend requires the
     * user's current password in the body to confirm identity, even though
     * they're already authenticated — a wrong one is a 401 UNAUTHORIZED, same
     * shape as `changePassword`. This does not, by itself, revoke the current
     * session — callers must still call `auth.logout()` afterward. */
    deleteMe: (body: { password: string }) =>
      apiFetch<void>("/users/me", { method: "DELETE", body }),
  },
  financialPeriods: {
    list: (query?: { year?: number; status?: string; page?: number; page_size?: number }) =>
      apiFetch<Paginated<FinancialPeriod>>("/financial-periods", { query }),
    /** Returns the current calendar month's period, creating it first if this is
     * the user's first visit this month (see `get_or_create_current` — there is no
     * "no period yet" empty state to handle here, the backend always returns one). */
    current: () => apiFetch<FinancialPeriod>("/financial-periods/current"),
    get: (id: string) => apiFetch<FinancialPeriod>(`/financial-periods/${id}`),
    create: (body: { year: number; month: number }) =>
      apiFetch<FinancialPeriod>("/financial-periods", { method: "POST", body }),
    close: (id: string) =>
      apiFetch<FinancialPeriod>(`/financial-periods/${id}/close`, { method: "POST" }),
    reopen: (id: string, body: { reason: string }) =>
      apiFetch<FinancialPeriod>(`/financial-periods/${id}/reopen`, { method: "POST", body }),
    summary: (id: string) =>
      apiFetch<MonthlySummary>(`/financial-periods/${id}/summary`),
    /** Sets which distribution rule this period uses. 409 if the period is
     * CLOSED — surfaced as-is, never silently ignored (spec §5/§37). */
    selectDistributionRule: (id: string, body: { distribution_rule_id: string }) =>
      apiFetch<FinancialPeriod>(`/financial-periods/${id}/select-distribution-rule`, {
        method: "POST",
        body,
      }),
  },
  savings: {
    get: (periodId: string) => apiFetch<SavingsSummary>(`/savings/${periodId}`),
  },
  // Manual, period-scoped savings entries (Phase 5 part 4) — a plain `MoneyInManager` shape,
  // same as allowances/income. NOTE (confirmed live): creating/updating/deleting one of these
  // does NOT synchronously refresh the `/savings/{period_id}` rollup — that cache row is only
  // recalculated the next time `GET /financial-periods/{id}/summary` runs. `lib/use-savings-summary.ts`
  // calls that first so the rollup shown on this page is never stale by a request.
  savingsItems: {
    list: (query?: { financial_period_id?: string; page?: number; page_size?: number }) =>
      apiFetch<Paginated<SavingsItem>>("/savings-items", { query }),
    create: (body: {
      financial_period_id: string;
      name: string;
      amount: string;
      currency: string;
      date: string;
      destination?: string | null;
      notes?: string | null;
    }) => apiFetch<SavingsItem>("/savings-items", { method: "POST", body }),
    update: (
      id: string,
      body: {
        name?: string;
        amount?: string;
        currency?: string;
        date?: string;
        destination?: string | null;
        notes?: string | null;
        expected_updated_at: string;
      },
    ) => apiFetch<SavingsItem>(`/savings-items/${id}`, { method: "PATCH", body }),
    remove: (id: string) => apiFetch<void>(`/savings-items/${id}`, { method: "DELETE" }),
  },
  // Savings distribution rule CRUD (D-013) — the savings-side analogue of `distributionRules`
  // above: a reusable name + sum-to-100 item list, each item pointing at a real bank account
  // or a free-text destination.
  savingsDistributionRules: {
    list: (query?: { is_active?: boolean; page?: number; page_size?: number }) =>
      apiFetch<Paginated<SavingsDistributionRule>>("/savings-distribution-rules", { query }),
    create: (body: { name: string; items: SavingsDistributionRuleItemInput[] }) =>
      apiFetch<SavingsDistributionRule>("/savings-distribution-rules", { method: "POST", body }),
    get: (id: string) => apiFetch<SavingsDistributionRule>(`/savings-distribution-rules/${id}`),
    update: (
      id: string,
      body: { name?: string; is_active?: boolean; is_default?: boolean; expected_updated_at: string },
    ) =>
      apiFetch<SavingsDistributionRule>(`/savings-distribution-rules/${id}`, {
        method: "PATCH",
        body,
      }),
    /** Full replace of the item set — same upsert-by-id/remove-if-missing convention as
     * `distributionRules.replaceCategories`. */
    replaceItems: (
      id: string,
      body: { items: SavingsDistributionRuleItemInput[]; expected_updated_at: string },
    ) =>
      apiFetch<SavingsDistributionRule>(`/savings-distribution-rules/${id}/items`, {
        method: "PUT",
        body,
      }),
  },
  // Where saved money is actually sent (D-014, §19/§20). `create` is the manual path; `applyRule`
  // regenerates the full AUTO set for a period from a rule and never stacks with a previous
  // apply (confirmed live). Deleting an individual AUTO row is rejected server-side (422) — the
  // UI never offers a delete action for one.
  savingsAllocations: {
    list: (query: { financial_period_id: string; allocation_method?: string; page?: number; page_size?: number }) =>
      apiFetch<Paginated<SavingsAllocation>>("/savings-allocations", { query }),
    create: (body: {
      financial_period_id: string;
      bank_account_id?: string | null;
      destination_label?: string | null;
      amount: string;
      transaction_date?: string | null;
    }) => apiFetch<SavingsAllocation>("/savings-allocations", { method: "POST", body }),
    applyRule: (body: { financial_period_id: string; savings_distribution_rule_id: string }) =>
      apiFetch<SavingsAllocation[]>("/savings-allocations/apply-rule", { method: "POST", body }),
    remove: (id: string) => apiFetch<void>(`/savings-allocations/${id}`, { method: "DELETE" }),
  },
  bankAccounts: {
    list: (query?: { is_active?: boolean; page?: number; page_size?: number }) =>
      apiFetch<Paginated<BankAccountSummary>>("/bank-accounts", { query }),
    create: (body: {
      account_name: string;
      institution_name?: string | null;
      account_type?: BankAccountType | null;
      account_identifier?: string | null;
      currency?: string;
      opening_balance?: string;
    }) => apiFetch<BankAccountSummary>("/bank-accounts", { method: "POST", body }),
    get: (id: string) => apiFetch<BankAccountSummary>(`/bank-accounts/${id}`),
    /** Also used to reactivate a deactivated account (`is_active: true`) — see
     * BankAccountUpdate on the backend. `account_identifier`, if supplied, is re-derived into
     * a new `account_identifier_last4` and the raw value is never echoed back or displayed
     * again — never pre-fill this field from an existing account when editing. */
    update: (
      id: string,
      body: {
        account_name?: string;
        institution_name?: string | null;
        account_type?: BankAccountType | null;
        account_identifier?: string | null;
        notes?: string | null;
        is_active?: boolean;
        expected_updated_at: string;
      },
    ) => apiFetch<BankAccountSummary>(`/bank-accounts/${id}`, { method: "PATCH", body }),
    /** Soft-deactivates only — never a hard delete (accounts and their transaction history
     * persist). Reverse with `update(id, { is_active: true, ... })`. */
    deactivate: (id: string) => apiFetch<void>(`/bank-accounts/${id}`, { method: "DELETE" }),
  },
  // A period-scoped, append-only ledger view (Phase 5 part 4). `create` covers
  // DEPOSIT/WITHDRAWAL/ADJUSTMENT only — TRANSFER_IN/TRANSFER_OUT are system-generated by
  // `transfer` alone, confirmed live never directly postable via `create`.
  bankTransactions: {
    list: (query?: {
      bank_account_id?: string;
      financial_period_id?: string;
      transaction_type?: string;
      date_from?: string;
      date_to?: string;
      page?: number;
      page_size?: number;
    }) => apiFetch<Paginated<BankTransaction>>("/bank-transactions", { query }),
    create: (body: {
      bank_account_id: string;
      financial_period_id: string;
      transaction_type: Exclude<BankTransactionType, "TRANSFER_IN" | "TRANSFER_OUT">;
      amount: string;
      currency: string;
      transaction_date: string;
      description?: string | null;
    }) => apiFetch<BankTransaction>("/bank-transactions", { method: "POST", body }),
    transfer: (body: {
      source_bank_account_id: string;
      destination_bank_account_id: string;
      financial_period_id: string;
      amount: string;
      currency: string;
      transaction_date: string;
      description?: string | null;
    }) => apiFetch<BankTransferResult>("/bank-transactions/transfer", { method: "POST", body }),
    get: (id: string) => apiFetch<BankTransaction>(`/bank-transactions/${id}`),
  },
  // Read-only, server-computed per-period breakdown (Phase 5 part 3) — distinct from
  // `distributionRules` below (CRUD rule definitions). See the `DistributionView`
  // doc comment in lib/types.ts. Confirmed live: a period with no rule selected
  // returns 200 with nulls/empty categories, not an error.
  distributions: {
    get: (periodId: string) => apiFetch<DistributionView>(`/distributions/${periodId}`),
  },
  // Distribution rule CRUD (Phase 3 backend, wired to the UI in Phase 5 part 3).
  // Percentage sum-to-100 and single-unallocated-bucket invariants are enforced
  // server-side on every create/replace — the frontend's running-total display is
  // strictly a UX nicety, never the actual gate (CLAUDE.md).
  distributionRules: {
    list: (query?: { is_active?: boolean; page?: number; page_size?: number }) =>
      apiFetch<Paginated<DistributionRule>>("/distribution-rules", { query }),
    create: (body: {
      name: string;
      description?: string | null;
      categories: DistributionCategoryInput[];
    }) => apiFetch<DistributionRule>("/distribution-rules", { method: "POST", body }),
    get: (id: string) => apiFetch<DistributionRule>(`/distribution-rules/${id}`),
    update: (
      id: string,
      body: {
        name?: string;
        description?: string | null;
        is_active?: boolean;
        is_default?: boolean;
        expected_updated_at: string;
      },
    ) => apiFetch<DistributionRule>(`/distribution-rules/${id}`, { method: "PATCH", body }),
    /** Full replace of the category set — rows with an `id` update in place, rows
     * without one are created, and any existing row not present is removed. */
    replaceCategories: (
      id: string,
      body: { categories: DistributionCategoryInput[]; expected_updated_at: string },
    ) =>
      apiFetch<DistributionRule>(`/distribution-rules/${id}/categories`, {
        method: "PUT",
        body,
      }),
    /** Deactivates the rule (soft — never a hard delete). 409 if it's the active
     * selection for an open period; surfaced as-is. */
    remove: (id: string) => apiFetch<void>(`/distribution-rules/${id}`, { method: "DELETE" }),
  },
  expenses: {
    list: (query?: {
      financial_period_id?: string;
      distribution_category_id?: string;
      page?: number;
      page_size?: number;
    }) => apiFetch<Paginated<Expense>>("/expenses", { query }),
    create: (body: {
      financial_period_id: string;
      distribution_category_id?: string | null;
      name: string;
      expense_category: ExpenseCategory;
      amount: string;
      currency: string;
      expense_date: string;
      payment_method?: PaymentMethod | null;
      bank_account_id?: string | null;
      notes?: string | null;
    }) => apiFetch<Expense>("/expenses", { method: "POST", body }),
    update: (
      id: string,
      body: {
        distribution_category_id?: string | null;
        name?: string;
        expense_category?: ExpenseCategory;
        amount?: string;
        currency?: string;
        expense_date?: string;
        payment_method?: PaymentMethod | null;
        bank_account_id?: string | null;
        notes?: string | null;
        expected_updated_at: string;
      },
    ) => apiFetch<Expense>(`/expenses/${id}`, { method: "PATCH", body }),
    remove: (id: string) => apiFetch<void>(`/expenses/${id}`, { method: "DELETE" }),
  },
  // Money-in modules (Phase 5 part 2): salary is one-per-period (D-008 — a
  // second create for the same period returns 409 CONFLICT, surfaced as-is,
  // never swallowed); allowances and income are unlimited per-period lists
  // (spec §7/§8). All three send Decimal amounts as raw strings the user typed
  // (never `Number(...)`-round-tripped) so precision is never touched by the
  // frontend — see lib/money.ts. Updates carry `expected_updated_at` — the
  // `updated_at` this tab last read for that record — as a body field per
  // D-018; a stale value is rejected with 409, not silently applied.
  salaries: {
    list: (query?: { financial_period_id?: string; page?: number; page_size?: number }) =>
      apiFetch<Paginated<Salary>>("/salaries", { query }),
    create: (body: {
      financial_period_id: string;
      net_amount: string;
      currency: string;
      status?: SalaryStatus;
      notes?: string | null;
    }) => apiFetch<Salary>("/salaries", { method: "POST", body }),
    update: (
      id: string,
      body: {
        net_amount?: string;
        currency?: string;
        status?: SalaryStatus;
        notes?: string | null;
        expected_updated_at: string;
      },
    ) => apiFetch<Salary>(`/salaries/${id}`, { method: "PATCH", body }),
    remove: (id: string) => apiFetch<void>(`/salaries/${id}`, { method: "DELETE" }),
  },
  allowances: {
    list: (query?: { financial_period_id?: string; page?: number; page_size?: number }) =>
      apiFetch<Paginated<Allowance>>("/allowances", { query }),
    create: (body: {
      financial_period_id: string;
      name: string;
      amount: string;
      currency: string;
      is_recurring?: boolean;
      date_received: string;
      notes?: string | null;
    }) => apiFetch<Allowance>("/allowances", { method: "POST", body }),
    update: (
      id: string,
      body: {
        name?: string;
        amount?: string;
        currency?: string;
        is_recurring?: boolean;
        date_received?: string;
        notes?: string | null;
        expected_updated_at: string;
      },
    ) => apiFetch<Allowance>(`/allowances/${id}`, { method: "PATCH", body }),
    remove: (id: string) => apiFetch<void>(`/allowances/${id}`, { method: "DELETE" }),
  },
  income: {
    list: (query?: { financial_period_id?: string; page?: number; page_size?: number }) =>
      apiFetch<Paginated<IncomeRecord>>("/income", { query }),
    create: (body: {
      financial_period_id: string;
      income_type: IncomeType;
      description: string;
      amount: string;
      currency: string;
      date_received: string;
      source?: string | null;
      is_recurring?: boolean;
      notes?: string | null;
    }) => apiFetch<IncomeRecord>("/income", { method: "POST", body }),
    update: (
      id: string,
      body: {
        income_type?: IncomeType;
        description?: string;
        amount?: string;
        currency?: string;
        date_received?: string;
        source?: string | null;
        is_recurring?: boolean;
        notes?: string | null;
        expected_updated_at: string;
      },
    ) => apiFetch<IncomeRecord>(`/income/${id}`, { method: "PATCH", body }),
    remove: (id: string) => apiFetch<void>(`/income/${id}`, { method: "DELETE" }),
  },
  // Reports module (Phase 5 part 5) — deliberately thin (spec: reports/exports are mostly
  // Phase 6 work). `monthlySummary` returns the exact same `MonthlySummaryRead` shape as
  // `financialPeriods.summary` (confirmed live, byte-for-byte field set) but is the actual
  // "report" endpoint, so the Reports page calls this one rather than reusing the dashboard's
  // call. Every other report type 501s by deliberate backend design — this file intentionally
  // has no wrapper for them; the Reports page lists those as "coming soon" instead of calling
  // an endpoint built to fail.
  reports: {
    monthlySummary: (periodId: string) =>
      apiFetch<MonthlySummary>(`/reports/monthly-summary/${periodId}`),
  },
};
