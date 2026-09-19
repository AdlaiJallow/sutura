"use client";

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
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { BankAccountList } from "./bank-account-list";
import { api, ApiError } from "@/lib/api";
import { humanizeEnum } from "@/lib/text";
import type { BankAccountSummary, BankAccountType } from "@/lib/types";

/**
 * Self-contained bank account CRUD (fetch + create/edit dialogs + activate/
 * deactivate), deliberately not built on `MoneyInManager` for the same reason
 * `distribution-rule-manager.tsx` isn't: the shape genuinely differs. Bank
 * accounts aren't period-scoped (no closed-period gate, no `financial_period_id`
 * on any payload — CLAUDE.md/task brief: "don't wire it to usePeriod()"), and
 * "delete" here is a reversible deactivate/reactivate rather than a permanent
 * remove, with its own confirmation copy. Modeled on
 * `DistributionRulesManager`'s self-contained fetch/CRUD shape instead.
 */

const ACCOUNT_TYPES: BankAccountType[] = ["BANK", "MOBILE_MONEY", "CASH", "SAVINGS", "INVESTMENT", "OTHER"];
const AMOUNT_RE = /^\d+(\.\d{1,4})?$/;
const CURRENCY_RE = /^[A-Za-z]{3}$/;

function AccountForm({
  title,
  submitLabel,
  initial,
  showIdentifierNote,
  onSubmit,
}: {
  title: string;
  submitLabel: string;
  initial: {
    account_name: string;
    institution_name: string;
    account_type: BankAccountType;
    account_identifier: string;
    currency: string;
    opening_balance: string;
    notes: string;
  };
  showIdentifierNote: boolean;
  onSubmit: (values: typeof initial) => Promise<void>;
}) {
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function setField<K extends keyof typeof initial>(key: K, value: (typeof initial)[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (!values.account_name.trim()) nextErrors.account_name = "Give this account a name.";
    if (!CURRENCY_RE.test(values.currency.trim())) {
      nextErrors.currency = "Currency must be a 3-letter code, e.g. GMD.";
    }
    if (values.opening_balance.trim() && !AMOUNT_RE.test(values.opening_balance.trim())) {
      nextErrors.opening_balance = "Enter an amount of 0 or more, e.g. 5000 or 5000.50.";
    }
    setErrors(nextErrors);
    setBanner(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await onSubmit(values);
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't save this account. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>

      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="account-name">Account name</Label>
        <Input
          id="account-name"
          value={values.account_name}
          placeholder="e.g. Main Checking"
          onChange={(e) => setField("account_name", e.target.value)}
        />
        {errors.account_name && <p className="text-xs text-overspent">{errors.account_name}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="account-institution">Institution</Label>
        <Input
          id="account-institution"
          value={values.institution_name}
          placeholder="e.g. Trust Bank — optional"
          onChange={(e) => setField("institution_name", e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="account-type">Type</Label>
          <Select value={values.account_type} onValueChange={(v) => setField("account_type", v as BankAccountType)}>
            <SelectTrigger id="account-type" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ACCOUNT_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {humanizeEnum(t)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="account-currency">Currency</Label>
          <Input
            id="account-currency"
            value={values.currency}
            maxLength={3}
            className="uppercase"
            onChange={(e) => setField("currency", e.target.value.toUpperCase())}
          />
          {errors.currency && <p className="text-xs text-overspent">{errors.currency}</p>}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="account-identifier">Account or card number</Label>
        <Input
          id="account-identifier"
          value={values.account_identifier}
          placeholder={showIdentifierNote ? "Leave blank to keep the current one on file" : "Optional"}
          onChange={(e) => setField("account_identifier", e.target.value)}
        />
        <p className="text-xs text-ink-faint">
          We only ever show the last 4 digits after this is saved — the full number is never displayed again.
        </p>
      </div>

      {!showIdentifierNote && (
        <div className="space-y-1.5">
          <Label htmlFor="account-opening-balance">Opening balance</Label>
          <Input
            id="account-opening-balance"
            inputMode="decimal"
            value={values.opening_balance}
            placeholder="0.00"
            onChange={(e) => setField("opening_balance", e.target.value)}
          />
          {errors.opening_balance && <p className="text-xs text-overspent">{errors.opening_balance}</p>}
        </div>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="account-notes">Notes</Label>
        <textarea
          id="account-notes"
          value={values.notes}
          onChange={(e) => setField("notes", e.target.value)}
          rows={2}
          placeholder="Optional"
          className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm text-ink outline-none focus-visible:border-rust-500"
        />
      </div>

      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : submitLabel}
        </Button>
      </DialogFooter>
    </form>
  );
}

function CreateAccountDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Add account</Button>
      </DialogTrigger>
      <DialogContent>
        {open && (
          <AccountForm
            title="Add a bank account"
            submitLabel="Add account"
            showIdentifierNote={false}
            initial={{
              account_name: "",
              institution_name: "",
              account_type: "BANK",
              account_identifier: "",
              currency: "GMD",
              opening_balance: "0",
              notes: "",
            }}
            onSubmit={async (values) => {
              await api.bankAccounts.create({
                account_name: values.account_name.trim(),
                institution_name: values.institution_name.trim() || null,
                account_type: values.account_type,
                account_identifier: values.account_identifier.trim() || null,
                currency: values.currency.trim().toUpperCase(),
                opening_balance: values.opening_balance.trim() || "0",
              });
              setOpen(false);
              onCreated();
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function EditAccountDialog({
  account,
  open,
  onOpenChange,
  onSaved,
}: {
  account: BankAccountSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && (
          <AccountForm
            title={`Edit ${account.account_name}`}
            submitLabel="Save changes"
            showIdentifierNote
            initial={{
              account_name: account.account_name,
              institution_name: account.institution_name ?? "",
              account_type: (account.account_type as BankAccountType) ?? "BANK",
              account_identifier: "",
              currency: account.currency,
              opening_balance: String(Number(account.opening_balance)),
              notes: account.notes ?? "",
            }}
            onSubmit={async (values) => {
              await api.bankAccounts.update(account.id, {
                account_name: values.account_name.trim(),
                institution_name: values.institution_name.trim() || null,
                account_type: values.account_type,
                account_identifier: values.account_identifier.trim() || undefined,
                notes: values.notes.trim() || null,
                expected_updated_at: account.updated_at,
              });
              onOpenChange(false);
              onSaved();
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function ToggleActiveDialog({
  account,
  open,
  onOpenChange,
  onDone,
}: {
  account: BankAccountSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const deactivating = account.is_active;

  async function handleConfirm() {
    setSubmitting(true);
    setBanner(null);
    try {
      if (deactivating) {
        await api.bankAccounts.deactivate(account.id);
      } else {
        await api.bankAccounts.update(account.id, { is_active: true, expected_updated_at: account.updated_at });
      }
      onOpenChange(false);
      onDone();
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't update this account. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{deactivating ? `Deactivate "${account.account_name}"?` : `Reactivate "${account.account_name}"?`}</DialogTitle>
          <DialogDescription>
            {deactivating
              ? "It won't be offered for new expenses, transactions, or savings destinations, but its balance and history stay exactly as they are."
              : "It becomes available again for new expenses, transactions, and savings destinations."}
          </DialogDescription>
        </DialogHeader>
        {banner && (
          <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
            {banner}
          </p>
        )}
        <DialogFooter>
          <Button variant={deactivating ? "destructive" : "default"} onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Saving…" : deactivating ? "Deactivate" : "Reactivate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function BankAccountsManager() {
  const [accounts, setAccounts] = useState<BankAccountSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<BankAccountSummary | null>(null);
  const [toggling, setToggling] = useState<BankAccountSummary | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.bankAccounts.list({ page_size: 100 });
      setAccounts(res.data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your bank accounts.");
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <CreateAccountDialog onCreated={load} />
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {!error && accounts === null && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-40 animate-pulse rounded-md bg-secondary" />
          ))}
        </div>
      )}

      {!error && accounts !== null && accounts.length === 0 && (
        <EmptyState
          title="No accounts yet"
          message="Add a bank account, mobile wallet, or cash pot to track balances and send savings there."
          action={<CreateAccountDialog onCreated={load} />}
        />
      )}

      {!error && accounts !== null && accounts.length > 0 && (
        <BankAccountList accounts={accounts} onEdit={setEditing} onToggleActive={setToggling} />
      )}

      {editing && (
        <EditAccountDialog account={editing} open={editing !== null} onOpenChange={(o) => !o && setEditing(null)} onSaved={load} />
      )}
      {toggling && (
        <ToggleActiveDialog account={toggling} open={toggling !== null} onOpenChange={(o) => !o && setToggling(null)} onDone={load} />
      )}
    </div>
  );
}
