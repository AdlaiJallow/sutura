"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useParams } from "next/navigation";
import { AmountDisplay } from "@/components/finance/amount-display";
import { StatusBadge } from "@/components/finance/status-badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { ErrorState } from "@/components/layout/error-state";
import { usePeriod } from "@/components/layout/period-context";
import { api, ApiError } from "@/lib/api";
import { monthLabel } from "@/lib/text";
import type { FinancialPeriod, MonthlySummary } from "@/lib/types";

/**
 * A single month, in full: status, the same live summary figures the dashboard
 * shows, and the close/reopen actions (spec §37 — closing/reopening a period is
 * an explicit, audited action, never a casual edit).
 */
export default function FinancialPeriodDetailPage() {
  const params = useParams<{ id: string }>();
  const periodId = params.id;
  const { refresh: refreshShellPeriods } = usePeriod();

  const [period, setPeriod] = useState<FinancialPeriod | null>(null);
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [periodRes, summaryRes] = await Promise.all([
        api.financialPeriods.get(periodId),
        api.financialPeriods.summary(periodId),
      ]);
      setPeriod(periodRes);
      setSummary(summaryRes);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong loading this period.",
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

  async function handleChanged(updated: FinancialPeriod) {
    setPeriod(updated);
    await Promise.all([load(), refreshShellPeriods()]);
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-56 animate-pulse rounded-md bg-secondary" />
        <div className="h-40 animate-pulse rounded-md bg-secondary" />
      </div>
    );
  }

  if (error || !period || !summary) {
    return <ErrorState message={error ?? undefined} onRetry={load} />;
  }

  const label = monthLabel(period.year, period.month);
  const currency = period.base_currency;

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold tracking-wideish text-rust-500 uppercase">
            <span>{label}</span>
            <StatusBadge status={period.status} />
            {period.reopened_count > 0 && <StatusBadge status="MODIFIED" />}
          </div>
          <h1 className="mt-2 font-display text-3xl text-ink">{label}</h1>
          <p className="mt-1 text-sm text-ink-soft">
            {period.start_date} to {period.end_date}
            {period.reopened_count > 0 &&
              ` · reopened ${period.reopened_count} time${period.reopened_count === 1 ? "" : "s"}`}
          </p>
        </div>
        <div className="flex gap-2">
          {period.status === "OPEN" ? (
            <ClosePeriodAction period={period} onClosed={handleChanged} />
          ) : (
            <ReopenPeriodAction period={period} onReopened={handleChanged} />
          )}
        </div>
      </div>

      <section>
        <h2 className="font-display text-xl text-ink">This month, at a glance</h2>
        <p className="mt-1 text-xs text-ink-faint">
          {period.status === "OPEN"
            ? "Recalculated live as you add records."
            : "Frozen at the numbers this period had when it was closed."}
        </p>
        <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-3">
          <Stat label="Total Monthly Income" value={summary.total_monthly_income} currency={currency} emphasize />
          <Stat label="Total Expenses" value={summary.total_expenses} currency={currency} />
          <Stat label="Final Savings" value={summary.final_savings} currency={currency} tone="positive" />
          <Stat label="Salary & Allowances" value={summary.total_salary_income} currency={currency} />
          <Stat label="Other Income" value={summary.total_other_income} currency={currency} />
          <Stat
            label="Undistributed Savings"
            value={summary.undistributed_savings}
            currency={currency}
            tone="auto"
          />
        </div>
      </section>

      <section>
        <h2 className="font-display text-xl text-ink">Distribution rule</h2>
        <p className="mt-2 text-sm text-ink-soft">
          {period.distribution_rule_id
            ? "A distribution rule is selected for this period."
            : "No distribution rule selected yet for this period."}
        </p>
      </section>
    </div>
  );
}

function ClosePeriodAction({
  period,
  onClosed,
}: {
  period: FinancialPeriod;
  onClosed: (period: FinancialPeriod) => void;
}) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleConfirm() {
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const updated = await api.financialPeriods.close(period.id);
      setOpen(false);
      onClosed(updated);
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Couldn't close this period.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">Close period</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Close {monthLabel(period.year, period.month)}?</DialogTitle>
          <DialogDescription>
            This freezes the month&apos;s summary. You can still reopen it later, but reopening is
            logged and shown as a modification.
          </DialogDescription>
        </DialogHeader>
        {errorMessage && (
          <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
            {errorMessage}
          </p>
        )}
        <DialogFooter>
          <Button variant="destructive" onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Closing…" : "Close this period"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ReopenPeriodAction({
  period,
  onReopened,
}: {
  period: FinancialPeriod;
  onReopened: (period: FinancialPeriod) => void;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!reason.trim()) {
      setFieldError("Tell us why you're reopening this period.");
      return;
    }
    setSubmitting(true);
    setFieldError(null);
    try {
      const updated = await api.financialPeriods.reopen(period.id, { reason: reason.trim() });
      setOpen(false);
      setReason("");
      onReopened(updated);
    } catch (err) {
      setFieldError(err instanceof ApiError ? err.message : "Couldn't reopen this period.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">Reopen period</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Reopen {monthLabel(period.year, period.month)}?</DialogTitle>
            <DialogDescription>
              A reason is required — it&apos;s recorded with this period&apos;s audit history and
              shown as &quot;Modified since close.&quot;
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="reopen-reason">Reason</Label>
            <textarea
              id="reopen-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm text-ink outline-none focus-visible:border-rust-500"
              placeholder="e.g. Forgot to log a grocery expense"
            />
            {fieldError && <p className="text-xs text-overspent">{fieldError}</p>}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Reopening…" : "Reopen this period"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Stat({
  label,
  value,
  currency,
  tone = "neutral",
  emphasize = false,
}: {
  label: string;
  value: string;
  currency: string;
  tone?: "neutral" | "positive" | "auto";
  emphasize?: boolean;
}) {
  return (
    <div className={emphasize ? "bg-accent p-4" : "bg-card p-4"}>
      <p className="text-[0.6875rem] font-medium tracking-wideish text-ink-faint uppercase">{label}</p>
      <AmountDisplay
        value={value}
        currency={currency}
        size={emphasize ? "lg" : "md"}
        tone={tone}
        weight={emphasize ? "semibold" : "medium"}
        className="mt-1"
      />
    </div>
  );
}
