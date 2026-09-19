"use client";

import { useCallback, useEffect, useState } from "react";
import { DashboardView } from "./dashboard-view";
import { DashboardLoadingSkeleton } from "./loading-skeleton";
import { ErrorState } from "@/components/layout/error-state";
import { usePeriod } from "@/components/layout/period-context";
import { api, ApiError } from "@/lib/api";
import type { BankAccountSummary, MonthlySummary, SavingsSummary } from "@/lib/types";

// Spec §21: income, spending, and savings totals, all straight from
// `GET /financial-periods/{id}/summary`, `GET /savings/{period_id}`, and
// `GET /bank-accounts` (Phase 5 part 1). A client component, not a server one:
// the access token lives only in an in-memory JS variable (D-026), which a
// server component has no way to read.
export default function DashboardPage() {
  const { period } = usePeriod();
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [savings, setSavings] = useState<SavingsSummary | null>(null);
  const [accounts, setAccounts] = useState<BankAccountSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, savingsRes, accountsRes] = await Promise.all([
        api.financialPeriods.summary(period.id),
        api.savings.get(period.id),
        api.bankAccounts.list({ page_size: 100 }),
      ]);
      setSummary(summaryRes);
      setSavings(savingsRes);
      setAccounts(accountsRes.data);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong loading this month's numbers. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [period.id]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  if (loading) return <DashboardLoadingSkeleton />;
  if (error || !summary || !savings || !accounts) {
    return <ErrorState message={error ?? undefined} onRetry={load} />;
  }

  return <DashboardView period={period} summary={summary} savings={savings} accounts={accounts} />;
}
