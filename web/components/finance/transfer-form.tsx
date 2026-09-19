"use client";

import { useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { defaultDateReceived } from "./money-in-manager";
import { ApiError } from "@/lib/api";
import type { BankAccountSummary } from "@/lib/types";

const AMOUNT_RE = /^\d+(\.\d{1,4})?$/;

export interface TransferPayload {
  source_bank_account_id: string;
  destination_bank_account_id: string;
  amount: string;
  currency: string;
  transaction_date: string;
  description: string | null;
}

export interface TransferFormProps {
  /** Only *active* accounts should ever be offered — an inactive one is rejected
   * server-side anyway (422), so it's never worth listing as a choice here. */
  accounts: BankAccountSummary[];
  onSubmit: (payload: TransferPayload) => Promise<void>;
}

function accountLabel(a: BankAccountSummary): string {
  return a.account_identifier_last4 ? `${a.account_name} ••${a.account_identifier_last4}` : a.account_name;
}

/**
 * A transfer is its own thing, not a "deposit with two accounts" — two
 * pickers, no transaction-type selector, and currency derived from the
 * accounts (the backend requires the amount's currency to match *both* legs
 * exactly, confirmed live) rather than free-typed, so the one currency
 * mismatch a transfer can actually have — source and destination using
 * different currencies — is caught here in plain language before a round trip.
 *
 * Deliberately presentational: `onSubmit` is a prop (same convention as
 * `RecordForm` inside `money-in-manager.tsx`) so this is directly unit
 * testable with a fixture account list and a `vi.fn()`, without mocking `api`
 * or a financial period.
 */
export function TransferForm({ accounts, onSubmit }: TransferFormProps) {
  const [sourceId, setSourceId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(defaultDateReceived());
  const [description, setDescription] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const accountsById = useMemo(() => new Map(accounts.map((a) => [a.id, a])), [accounts]);
  const sourceAccount = sourceId ? accountsById.get(sourceId) : undefined;
  const destinationAccount = destinationId ? accountsById.get(destinationId) : undefined;
  const currencyMismatch =
    sourceAccount && destinationAccount && sourceAccount.currency !== destinationAccount.currency;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (!sourceId) nextErrors.source = "Choose the account to move money from.";
    if (!destinationId) nextErrors.destination = "Choose the account to move money to.";
    if (sourceId && destinationId && sourceId === destinationId) {
      nextErrors.destination = "Choose a different account than the source.";
    }
    if (!amount.trim() || !AMOUNT_RE.test(amount.trim())) {
      nextErrors.amount = "Enter an amount greater than 0, e.g. 500 or 500.50.";
    }
    if (!date) nextErrors.date = "Choose a date.";
    setErrors(nextErrors);
    setBanner(null);
    if (Object.keys(nextErrors).length > 0) return;

    if (currencyMismatch && sourceAccount && destinationAccount) {
      setBanner(
        `These accounts use different currencies (${sourceAccount.currency} vs ${destinationAccount.currency}) — a transfer needs both sides to match.`,
      );
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        source_bank_account_id: sourceId,
        destination_bank_account_id: destinationId,
        amount: amount.trim(),
        currency: (sourceAccount?.currency ?? "").toUpperCase(),
        transaction_date: date,
        description: description.trim() || null,
      });
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't complete this transfer. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Transfer between accounts</DialogTitle>
      </DialogHeader>

      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="transfer-source">From</Label>
        <Select value={sourceId} onValueChange={setSourceId}>
          <SelectTrigger id="transfer-source" className="w-full">
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
        {errors.source && <p className="text-xs text-overspent">{errors.source}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="transfer-destination">To</Label>
        <Select value={destinationId} onValueChange={setDestinationId}>
          <SelectTrigger id="transfer-destination" className="w-full">
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
        {errors.destination && <p className="text-xs text-overspent">{errors.destination}</p>}
      </div>

      {currencyMismatch && sourceAccount && destinationAccount && (
        <p className="text-xs text-overspent">
          {sourceAccount.account_name} is in {sourceAccount.currency}, but {destinationAccount.account_name} is in{" "}
          {destinationAccount.currency} — a transfer needs both sides to match.
        </p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="transfer-amount">Amount{sourceAccount ? ` (${sourceAccount.currency})` : ""}</Label>
          <Input
            id="transfer-amount"
            inputMode="decimal"
            value={amount}
            placeholder="e.g. 500"
            onChange={(e) => setAmount(e.target.value)}
          />
          {errors.amount && <p className="text-xs text-overspent">{errors.amount}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="transfer-date">Date</Label>
          <Input id="transfer-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          {errors.date && <p className="text-xs text-overspent">{errors.date}</p>}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="transfer-description">Description</Label>
        <Input
          id="transfer-description"
          value={description}
          placeholder="Optional"
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Transferring…" : "Transfer money"}
        </Button>
      </DialogFooter>
    </form>
  );
}
