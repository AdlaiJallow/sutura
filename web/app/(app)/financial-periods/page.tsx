"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { StatusBadge } from "@/components/finance/status-badge";
import { usePeriod } from "@/components/layout/period-context";
import { api, ApiError } from "@/lib/api";
import { monthLabel } from "@/lib/text";
import type { FinancialPeriod } from "@/lib/types";

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => i + 1);

/**
 * Every financial period this user has tracked, newest first, with the way in
 * to open a new one. Every other page (dashboard, salary, expenses...) hangs
 * off a `financial_period_id`, so this list — and the ability to create the
 * next month's period — is a gating dependency for the rest of the app
 * (frontend-routes.md).
 */
export default function FinancialPeriodsPage() {
  const router = useRouter();
  const { refresh: refreshShellPeriods } = usePeriod();
  const [periods, setPeriods] = useState<FinancialPeriod[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.financialPeriods.list({ page_size: 100 });
      setPeriods([...res.data].sort((a, b) => (a.year === b.year ? b.month - a.month : b.year - a.year)));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong loading your financial periods.",
      );
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function handleCreated(created: FinancialPeriod) {
    setDialogOpen(false);
    await Promise.all([load(), refreshShellPeriods()]);
    router.push(`/financial-periods/${created.id}`);
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-ink">Financial Periods</h1>
          <p className="mt-1 max-w-md text-sm text-ink-soft">
            Every month you&apos;ve tracked, with its status — and a way to open the next one.
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>New period</Button>
          </DialogTrigger>
          <DialogContent>
            <CreatePeriodForm onCreated={handleCreated} />
          </DialogContent>
        </Dialog>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {!error && periods === null && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md bg-secondary" />
          ))}
        </div>
      )}

      {!error && periods !== null && periods.length === 0 && (
        <EmptyState
          title="No financial periods yet"
          message="Create your first period to start recording salary, expenses, and savings."
          action={<Button onClick={() => setDialogOpen(true)}>New period</Button>}
        />
      )}

      {!error && periods !== null && periods.length > 0 && (
        <div className="overflow-hidden rounded-md border border-line">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Period</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Dates</TableHead>
                <TableHead className="text-right">&nbsp;</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {periods.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-display text-base text-ink">
                    {monthLabel(p.year, p.month)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={p.status} />
                      {p.reopened_count > 0 && <StatusBadge status="MODIFIED" />}
                    </div>
                  </TableCell>
                  <TableCell className="figure text-xs text-ink-faint">
                    {p.start_date} &ndash; {p.end_date}
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      href={`/financial-periods/${p.id}`}
                      className="text-sm font-medium text-rust-500 hover:text-rust-700"
                    >
                      View &rarr;
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function CreatePeriodForm({ onCreated }: { onCreated: (period: FinancialPeriod) => void }) {
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): string | null {
    const y = Number(year);
    const m = Number(month);
    if (!Number.isInteger(y) || y < 2000 || y > 2100) return "Enter a year between 2000 and 2100.";
    if (!Number.isInteger(m) || m < 1 || m > 12) return "Choose a month.";
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setFieldError(validationError);
      return;
    }
    setSubmitting(true);
    setFieldError(null);
    try {
      const created = await api.financialPeriods.create({ year: Number(year), month: Number(month) });
      onCreated(created);
    } catch (err) {
      setFieldError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong creating that period. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Start a new financial period</DialogTitle>
        <DialogDescription>
          One period per calendar month. You can&apos;t create a period that already exists.
        </DialogDescription>
      </DialogHeader>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="period-year">Year</Label>
          <Input
            id="period-year"
            type="number"
            inputMode="numeric"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            min={2000}
            max={2100}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="period-month">Month</Label>
          <Select value={month} onValueChange={setMonth}>
            <SelectTrigger id="period-month" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MONTH_OPTIONS.map((m) => (
                <SelectItem key={m} value={String(m)}>
                  {monthLabel(2000, m).split(" ")[0]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      {fieldError && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {fieldError}
        </p>
      )}
      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create period"}
        </Button>
      </DialogFooter>
    </form>
  );
}
