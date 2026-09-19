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

const TYPE_OPTIONS: { value: "DEPOSIT" | "WITHDRAWAL" | "ADJUSTMENT"; label: string }[] = [
  { value: "DEPOSIT", label: "Deposit (money in)" },
  { value: "WITHDRAWAL", label: "Withdrawal (money out)" },
  { value: "ADJUSTMENT", label: "Adjustment (correct the balance)" },
];

export interface TransactionPayload {
  bank_account_id: string;
  transaction_type: "DEPOSIT" | "WITHDRAWAL" | "ADJUSTMENT";
  amount: string;
  currency: string;
  transaction_date: string;
  description: string | null;
}

export interface TransactionFormProps {
  /** Only active accounts should ever be offered — an inactive one is rejected
   * server-side (422). TRANSFER_IN/TRANSFER_OUT are system-generated only
   * (see `TransferForm`) and never offered as a type here. */
  accounts: BankAccountSummary[];
  onSubmit: (payload: TransactionPayload) => Promise<void>;
}

function accountLabel(a: BankAccountSummary): string {
  return a.account_identifier_last4 ? `${a.account_name} ••${a.account_identifier_last4}` : a.account_name;
}

/**
 * A plain deposit/withdrawal/adjustment against one account — presentational,
 * same `onSubmit`-as-prop convention as `TransferForm`/`RecordForm` so it's
 * directly testable without mocking `api`. Currency is derived from the
 * chosen account (never free-typed) since the backend requires it to match
 * exactly (confirmed live: a mismatch is a 422).
 */
export function TransactionForm({ accounts, onSubmit }: TransactionFormProps) {
  const [accountId, setAccountId] = useState("");
  const [type, setType] = useState<"DEPOSIT" | "WITHDRAWAL" | "ADJUSTMENT">("DEPOSIT");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(defaultDateReceived());
  const [description, setDescription] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const accountsById = useMemo(() => new Map(accounts.map((a) => [a.id, a])), [accounts]);
  const account = accountId ? accountsById.get(accountId) : undefined;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (!accountId) nextErrors.account = "Choose an account.";
    if (!amount.trim() || !AMOUNT_RE.test(amount.trim())) {
      nextErrors.amount = "Enter an amount greater than 0, e.g. 500 or 500.50.";
    }
    if (!date) nextErrors.date = "Choose a date.";
    setErrors(nextErrors);
    setBanner(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await onSubmit({
        bank_account_id: accountId,
        transaction_type: type,
        amount: amount.trim(),
        currency: (account?.currency ?? "").toUpperCase(),
        transaction_date: date,
        description: description.trim() || null,
      });
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't record this transaction. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Add a transaction</DialogTitle>
      </DialogHeader>

      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="txn-account">Account</Label>
        <Select value={accountId} onValueChange={setAccountId}>
          <SelectTrigger id="txn-account" className="w-full">
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
        {errors.account && <p className="text-xs text-overspent">{errors.account}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="txn-type">Type</Label>
        <Select value={type} onValueChange={(v) => setType(v as typeof type)}>
          <SelectTrigger id="txn-type" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TYPE_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="txn-amount">Amount{account ? ` (${account.currency})` : ""}</Label>
          <Input
            id="txn-amount"
            inputMode="decimal"
            value={amount}
            placeholder="e.g. 500"
            onChange={(e) => setAmount(e.target.value)}
          />
          {errors.amount && <p className="text-xs text-overspent">{errors.amount}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="txn-date">Date</Label>
          <Input id="txn-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          {errors.date && <p className="text-xs text-overspent">{errors.date}</p>}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="txn-description">Description</Label>
        <Input
          id="txn-description"
          value={description}
          placeholder="Optional"
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Add transaction"}
        </Button>
      </DialogFooter>
    </form>
  );
}
