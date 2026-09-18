// Sutura API client — the ONLY place that talks to the FastAPI backend.
//
// Rules this file enforces for the rest of the app (see CLAUDE.md / frontend-engineer.md):
//   - Every monetary/derived figure comes back exactly as the API sent it (a string,
//     per api-contract.md §0) — nothing here parses it into a float and nothing
//     upstream should either. Formatting happens only in <AmountDisplay />.
//   - Errors are surfaced in the api-contract.md error envelope shape, never swallowed.
//   - The base URL is always read from NEXT_PUBLIC_API_URL — never hardcoded.

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
  method?: "GET" | "POST" | "PATCH" | "DELETE";
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

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem("sutura_access_token");
  } catch {
    return null;
  }
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
      credentials: "include", // httpOnly refresh cookie, per architecture.md §5
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
// Domain calls — thin, typed wrappers per docs/api-contract.md. Add new ones
// here as pages need them; never fetch() directly from a component.
// ---------------------------------------------------------------------------

import type {
  AuthTokens,
  DistributionView,
  FinancialPeriod,
  Paginated,
  PeriodSummary,
  SavingsSummary,
  BankAccountSummary,
  Expense,
  UserProfile,
} from "./types";

export const api = {
  auth: {
    register: (body: { email: string; password: string; full_name: string }) =>
      apiFetch<{ data: UserProfile }>("/auth/register", { method: "POST", body }),
    login: (body: { email: string; password: string }) =>
      apiFetch<{ data: AuthTokens }>("/auth/login", { method: "POST", body }),
  },
  financialPeriods: {
    list: (query?: { year?: number; status?: string; page?: number }) =>
      apiFetch<Paginated<FinancialPeriod>>("/financial-periods", { query }),
    current: () => apiFetch<{ data: FinancialPeriod }>("/financial-periods/current"),
    get: (id: string) => apiFetch<{ data: FinancialPeriod }>(`/financial-periods/${id}`),
    summary: (id: string) =>
      apiFetch<{ data: PeriodSummary }>(`/financial-periods/${id}/summary`),
  },
  distributions: {
    get: (periodId: string) =>
      apiFetch<{ data: DistributionView }>(`/distributions/${periodId}`),
  },
  savings: {
    get: (periodId: string) => apiFetch<{ data: SavingsSummary }>(`/savings/${periodId}`),
  },
  bankAccounts: {
    list: (query?: { is_active?: boolean }) =>
      apiFetch<Paginated<BankAccountSummary>>("/bank-accounts", { query }),
  },
  expenses: {
    list: (query?: { financial_period_id?: string; page?: number }) =>
      apiFetch<Paginated<Expense>>("/expenses", { query }),
  },
};
