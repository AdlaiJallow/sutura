"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
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
import { AmountDisplay } from "./amount-display";
import { StatusBadge } from "./status-badge";
import { defaultDateReceived } from "./money-in-manager";
import { api, ApiError } from "@/lib/api";
import type { BankAccountSummary, FinancialPeriod, SavingsAllocation, SavingsDistributionRule } from "@/lib/types";

const AMOUNT_RE = /^\d+(\.\d{1,4})?$/;

function accountLabel(a: BankAccountSummary): string {
  return a.account_identifier_last4 ? `${a.account_name} ••${a.account_identifier_last4}` : a.account_name;
}

function destinationLabel(allocation: SavingsAllocation, accountsById: Map<string, BankAccountSummary>) {
  if (allocation.bank_account_id) {
    const account = accountsById.get(allocation.bank_account_id);
    return account ? accountLabel(account) : "Unknown account";
  }
  return allocation.destination_label ?? "—";
}

function ApplyRuleControl({
  period,
  rules,
  onApplied,
}: {
  period: FinancialPeriod;
  rules: SavingsDistributionRule[];
  onApplied: () => void;
}) {
  const [ruleId, setRuleId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleApply() {
    if (!ruleId) {
      setError("Choose a rule first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.savingsAllocations.applyRule({ financial_period_id: period.id, savings_distribution_rule_id: ruleId });
      onApplied();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't apply this rule.");
    } finally {
      setSubmitting(false);
    }
  }

  if (rules.length === 0) return null;

  return (
    <div className="flex flex-wrap items-start gap-2">
      <Select value={ruleId} onValueChange={setRuleId}>
        <SelectTrigger className="w-56">
          <SelectValue placeholder="Choose a savings rule" />
        </SelectTrigger>
        <SelectContent>
          {rules.map((r) => (
            <SelectItem key={r.id} value={r.id}>
              {r.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button variant="outline" onClick={handleApply} disabled={submitting}>
        {submitting ? "Applying…" : "Apply rule"}
      </Button>
      {error && <p className="w-full text-xs text-overspent">{error}</p>}
    </div>
  );
}

function ManualAllocationDialog({
  period,
  accounts,
  onCreated,
}: {
  period: FinancialPeriod;
  accounts: BankAccountSummary[];
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"account" | "label">("account");
  const [bankAccountId, setBankAccountId] = useState("");
  const [destinationLabelValue, setDestinationLabelValue] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(defaultDateReceived());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setMode("account");
    setBankAccountId("");
    setDestinationLabelValue("");
    setAmount("");
    setDate(defaultDateReceived());
    setErrors({});
    setBanner(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (mode === "account" && !bankAccountId) nextErrors.destination = "Choose a bank account.";
    if (mode === "label" && !destinationLabelValue.trim()) nextErrors.destination = "Name this destination.";
    if (!amount.trim() || !AMOUNT_RE.test(amount.trim())) {
      nextErrors.amount = "Enter an amount greater than 0, e.g. 500 or 500.50.";
    }
    setErrors(nextErrors);
    setBanner(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await api.savingsAllocations.create({
        financial_period_id: period.id,
        bank_account_id: mode === "account" ? bankAccountId : null,
        destination_label: mode === "label" ? destinationLabelValue.trim() : null,
        amount: amount.trim(),
        transaction_date: date || null,
      });
      setOpen(false);
      reset();
      onCreated();
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't save this allocation. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button>Send savings manually</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Send savings to a destination</DialogTitle>
          </DialogHeader>

          {banner && (
            <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
              {banner}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3 text-xs text-ink-soft">
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="allocation-mode"
                checked={mode === "account"}
                onChange={() => setMode("account")}
                className="size-3.5 accent-rust-500"
              />
              Bank account
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                name="allocation-mode"
                checked={mode === "label"}
                onChange={() => setMode("label")}
                className="size-3.5 accent-rust-500"
              />
              Other destination
            </label>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="allocation-destination">Destination</Label>
            {mode === "account" ? (
              <Select value={bankAccountId} onValueChange={setBankAccountId}>
                <SelectTrigger id="allocation-destination" className="w-full">
                  <SelectValue placeholder="Choose an account" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {accountLabel(a)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                id="allocation-destination"
                value={destinationLabelValue}
                placeholder="e.g. Cash at home"
                onChange={(e) => setDestinationLabelValue(e.target.value)}
              />
            )}
            {errors.destination && <p className="text-xs text-overspent">{errors.destination}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="allocation-amount">Amount ({period.base_currency})</Label>
              <Input
                id="allocation-amount"
                inputMode="decimal"
                value={amount}
                placeholder="e.g. 500"
                onChange={(e) => setAmount(e.target.value)}
              />
              {errors.amount && <p className="text-xs text-overspent">{errors.amount}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="allocation-date">Date</Label>
              <Input id="allocation-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving…" : "Send"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function SavingsAllocationManager({
  period,
  accounts,
  rules,
  onAllocated,
}: {
  period: FinancialPeriod;
  accounts: BankAccountSummary[];
  rules: SavingsDistributionRule[];
  onAllocated: () => void;
}) {
  const [allocations, setAllocations] = useState<SavingsAllocation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const isClosed = period.status === "CLOSED";

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.savingsAllocations.list({ financial_period_id: period.id, page_size: 100 });
      setAllocations(res.data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load this period's savings allocations.");
    }
  }, [period.id]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function handleChanged() {
    await load();
    onAllocated();
  }

  async function handleDelete(allocation: SavingsAllocation) {
    setDeleteError(null);
    try {
      await api.savingsAllocations.remove(allocation.id);
      await handleChanged();
    } catch (err) {
      // AUTO allocations are rejected server-side (422) — surfaced as-is rather than hidden,
      // even though the delete action is only ever offered for MANUAL rows (task brief).
      setDeleteError(err instanceof ApiError ? err.message : "Couldn't remove this allocation.");
    }
  }

  const accountsById = new Map(accounts.map((a) => [a.id, a]));

  return (
    <div className="space-y-4">
      {!isClosed && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <ApplyRuleControl period={period} rules={rules} onApplied={handleChanged} />
          <ManualAllocationDialog period={period} accounts={accounts} onCreated={handleChanged} />
        </div>
      )}
      {isClosed && (
        <p className="rounded-md border border-line bg-secondary px-4 py-3 text-sm text-ink-soft">
          This period is closed, so savings can&apos;t be sent anywhere new here.
        </p>
      )}

      {deleteError && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {deleteError}
        </p>
      )}

      {error && <ErrorState message={error} onRetry={load} />}

      {!error && allocations === null && <div className="h-24 animate-pulse rounded-md bg-secondary" />}

      {!error && allocations !== null && allocations.length === 0 && (
        <EmptyState
          title="Nothing sent yet"
          message="Apply a savings rule or send an amount manually to see it here."
        />
      )}

      {!error && allocations !== null && allocations.length > 0 && (
        <div className="overflow-hidden rounded-md border border-line">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Destination</TableHead>
                <TableHead>Method</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right">&nbsp;</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {allocations.map((allocation) => (
                <TableRow key={allocation.id}>
                  <TableCell className="text-ink">{destinationLabel(allocation, accountsById)}</TableCell>
                  <TableCell>
                    <StatusBadge status={allocation.allocation_method === "AUTO" ? "AUTO" : "MANUAL"} />
                  </TableCell>
                  <TableCell className="text-right">
                    <AmountDisplay value={allocation.amount} currency={period.base_currency} />
                  </TableCell>
                  <TableCell className="text-right">
                    {!isClosed && allocation.allocation_method === "MANUAL" && (
                      <button
                        type="button"
                        onClick={() => handleDelete(allocation)}
                        className="text-sm font-medium text-overspent hover:text-overspent/80"
                      >
                        Delete
                      </button>
                    )}
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
