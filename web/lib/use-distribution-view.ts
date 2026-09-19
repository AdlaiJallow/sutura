// Shared fetch for `GET /distributions/{period_id}` — used by both the
// Distribution page (the breakdown itself) and the Expense form (which needs
// the period's real categories for its category select, and to know whether
// a category is required at all). One fetch/error/reload shape instead of two
// near-identical `useEffect`s, matching the `useMoneyInList` precedent.
"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "./api";
import type { DistributionView } from "./types";

export function useDistributionView(periodId: string) {
  const [view, setView] = useState<DistributionView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.distributions.get(periodId);
      setView(res);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Couldn't load this period's distribution. Please try again.",
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

  return { view, error, loading, reload: load };
}
