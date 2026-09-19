// Shared fetch for the Savings page's rollup — mirrors `use-distribution-view.ts`'s shape,
// with one extra step: `GET /savings/{period_id}` is a *cached* row that's only recalculated
// server-side the next time `GET /financial-periods/{id}/summary` runs (confirmed live against
// the running backend — a savings item, expense, or allocation created moments ago is NOT yet
// reflected in `/savings/{period_id}` until that recalculation happens). Rather than surprise
// every caller with stale numbers, this hook triggers that recalculation first and only then
// reads the rollup, so `summary` here is always current as of this call.
"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "./api";
import type { SavingsSummary } from "./types";

export function useSavingsSummary(periodId: string) {
  const [summary, setSummary] = useState<SavingsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await api.financialPeriods.summary(periodId);
      const res = await api.savings.get(periodId);
      setSummary(res);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Couldn't load this period's savings. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [periodId]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  return { summary, error, loading, reload: load };
}
