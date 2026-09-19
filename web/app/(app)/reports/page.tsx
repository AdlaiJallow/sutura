"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ComingSoonReports } from "@/components/reports/coming-soon-reports";
import { MonthlySummaryReport } from "@/components/reports/monthly-summary-report";
import { ErrorState } from "@/components/layout/error-state";
import { usePeriod } from "@/components/layout/period-context";
import { api, ApiError } from "@/lib/api";
import { monthLabel } from "@/lib/text";
import type { MonthlySummary } from "@/lib/types";

/**
 * Spec §32's `/reports` route. Only `GET /reports/monthly-summary/{period_id}`
 * is real on the backend today (`app/reports/router.py`'s own docstring: every
 * other report/export is Phase 6) — this page shows that one for real, for
 * whichever period the shell's period switcher currently has selected, and is
 * upfront about everything else not existing yet rather than hiding the gap
 * or faking it from data already on hand (CLAUDE.md).
 */
export default function ReportsPage() {
  const { period } = usePeriod();
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.reports.monthlySummary(period.id);
      setSummary(res);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Couldn't load this period's report. Please try again.",
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

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-start justify-between gap-4 print:hidden">
        <div>
          <h1 className="font-display text-3xl text-ink">Reports</h1>
          <p className="mt-1 max-w-md text-sm text-ink-soft">
            A formal record of {monthLabel(period.year, period.month)} you can print or save as a PDF
            from your browser.
          </p>
        </div>
        {summary && (
          <Button variant="outline" onClick={() => window.print()}>
            Print this report
          </Button>
        )}
      </div>

      {loading && (
        <div className="mx-auto max-w-2xl space-y-3">
          <div className="h-64 animate-pulse rounded-md bg-secondary" />
        </div>
      )}

      {!loading && (error || !summary) && (
        <ErrorState message={error ?? undefined} onRetry={load} />
      )}

      {!loading && summary && (
        <div className="mx-auto max-w-2xl">
          <MonthlySummaryReport period={period} summary={summary} />
        </div>
      )}

      <div className="print:hidden">
        <ComingSoonReports />
      </div>
    </div>
  );
}
