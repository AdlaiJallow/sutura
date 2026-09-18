"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { mockAllPeriods, mockCurrentPeriod } from "@/lib/mock-data";
import type { FinancialPeriod } from "@/lib/types";

interface PeriodContextValue {
  period: FinancialPeriod;
  periods: FinancialPeriod[];
  setPeriodId: (id: string) => void;
}

const PeriodContext = createContext<PeriodContextValue | null>(null);

/**
 * Holds the currently-selected `financial_period_id` for the whole app shell,
 * per frontend-routes.md's `PeriodSelector` ("drives the financial_period_id
 * used by every query on the page; persists selection across navigation").
 * In Phase 2 this reads/writes an in-memory list of mock periods; once
 * `GET /financial-periods` is wired in (Phase 3), this provider is the only
 * place that changes — no page below it needs to know the difference.
 */
export function PeriodProvider({ children }: { children: ReactNode }) {
  const [periods] = useState<FinancialPeriod[]>(mockAllPeriods);
  const [periodId, setPeriodId] = useState(mockCurrentPeriod.id);

  const value = useMemo<PeriodContextValue>(() => {
    const period = periods.find((p) => p.id === periodId) ?? periods[0];
    return { period, periods, setPeriodId };
  }, [periodId, periods]);

  return <PeriodContext.Provider value={value}>{children}</PeriodContext.Provider>;
}

export function usePeriod() {
  const ctx = useContext(PeriodContext);
  if (!ctx) throw new Error("usePeriod must be used within a PeriodProvider");
  return ctx;
}
