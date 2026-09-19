"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "@/lib/api";
import { ErrorState } from "./error-state";
import { Logo } from "@/components/brand/logo";
import type { FinancialPeriod } from "@/lib/types";

interface PeriodContextValue {
  period: FinancialPeriod;
  periods: FinancialPeriod[];
  setPeriodId: (id: string) => void;
  /** Re-fetches periods + current from the API — call after creating, closing, or
   * reopening a period so the header selector and every consumer stay in sync. */
  refresh: () => void;
}

const PeriodContext = createContext<PeriodContextValue | null>(null);

/**
 * Holds the currently-selected `financial_period_id` for the whole app shell,
 * per frontend-routes.md's `PeriodSelector` ("drives the financial_period_id
 * used by every query on the page; persists selection across navigation").
 *
 * Wired to real data: `GET /financial-periods/current` (which auto-creates the
 * current calendar month's period on first visit — there is no "brand new user,
 * zero periods" case to handle here) and `GET /financial-periods` for the full
 * list the selector offers.
 *
 * Gates its children entirely: nothing below this provider renders until a
 * period is loaded, so every page under it can assume `usePeriod().period` is
 * never null.
 */
export function PeriodProvider({ children }: { children: ReactNode }) {
  const [periods, setPeriods] = useState<FinancialPeriod[]>([]);
  const [periodId, setPeriodId] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const current = await api.financialPeriods.current();
      const list = await api.financialPeriods.list({ page_size: 100 });
      const merged = list.data.some((p) => p.id === current.id)
        ? list.data
        : [current, ...list.data];
      setPeriods(merged);
      setPeriodId((prev) => (prev && merged.some((p) => p.id === prev) ? prev : current.id));
      setStatus("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof ApiError
          ? err.message
          : "Couldn't load your financial periods. Check your connection and try again.",
      );
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  if (status === "loading") {
    return (
      <div className="flex min-h-full flex-1 flex-col items-center justify-center gap-4 px-4">
        <Logo size="lg" />
        <div className="h-1 w-40 overflow-hidden rounded-full bg-secondary">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-rust-500" />
        </div>
        <p className="text-sm text-ink-soft">Loading your financial periods…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="mx-auto flex min-h-full max-w-md flex-1 items-center px-4">
        <ErrorState
          title="Couldn't load your periods"
          message={errorMessage ?? undefined}
          onRetry={load}
          className="w-full"
        />
      </div>
    );
  }

  const period = periods.find((p) => p.id === periodId) ?? periods[0];

  return (
    <PeriodContext.Provider value={{ period, periods, setPeriodId, refresh: load }}>
      {children}
    </PeriodContext.Provider>
  );
}

export function usePeriod() {
  const ctx = useContext(PeriodContext);
  if (!ctx) throw new Error("usePeriod must be used within a PeriodProvider");
  return ctx;
}
