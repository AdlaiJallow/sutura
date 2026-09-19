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
  AuthTokens,
  BankAccountSummary,
  Expense,
  FinancialPeriod,
  MonthlySummary,
  Paginated,
  RegisterResult,
  SavingsSummary,
  UserProfile,
} from "./types";

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
  },
  savings: {
    get: (periodId: string) => apiFetch<SavingsSummary>(`/savings/${periodId}`),
  },
  bankAccounts: {
    list: (query?: { is_active?: boolean; page?: number; page_size?: number }) =>
      apiFetch<Paginated<BankAccountSummary>>("/bank-accounts", { query }),
  },
  expenses: {
    list: (query?: { financial_period_id?: string; page?: number; page_size?: number }) =>
      apiFetch<Paginated<Expense>>("/expenses", { query }),
  },
};
