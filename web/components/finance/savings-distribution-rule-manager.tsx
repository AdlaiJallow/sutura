"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { PlusIcon, XIcon } from "lucide-react";
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
import { StatusBadge } from "./status-badge";
import { api, ApiError, type SavingsDistributionRuleItemInput } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { BankAccountSummary, SavingsDistributionRule, SavingsDistributionRuleItem } from "@/lib/types";

/**
 * Savings-side analogue of `distribution-rule-manager.tsx`'s
 * `DistributionRulesManager` — same "name + nested, sum-to-100, variable-length
 * item list" shape (task brief: reuse that pattern rather than reinventing
 * it), adapted for the one real difference: each item points at either a real
 * bank account or a free-text destination label, never both/neither
 * (`_require_destination` server-side) — a per-row toggle picks which.
 */

type DestinationMode = "account" | "label";

interface ItemRow {
  key: string;
  id?: string;
  mode: DestinationMode;
  bank_account_id: string;
  destination_label: string;
  percentage: string;
}

let rowSeq = 0;
function blankRow(): ItemRow {
  rowSeq += 1;
  return { key: `new-${rowSeq}`, mode: "account", bank_account_id: "", destination_label: "", percentage: "" };
}

function rowFromItem(item: SavingsDistributionRuleItem): ItemRow {
  return {
    key: item.id,
    id: item.id,
    mode: item.bank_account_id ? "account" : "label",
    bank_account_id: item.bank_account_id ?? "",
    destination_label: item.destination_label ?? "",
    percentage: String(Number(item.percentage)),
  };
}

function runningTotal(rows: ItemRow[]): number {
  return rows.reduce((sum, r) => sum + (Number(r.percentage) || 0), 0);
}

function toPayload(rows: ItemRow[]): SavingsDistributionRuleItemInput[] {
  return rows.map((r) => ({
    id: r.id,
    bank_account_id: r.mode === "account" ? r.bank_account_id || null : null,
    destination_label: r.mode === "label" ? r.destination_label.trim() || null : null,
    percentage: r.percentage.trim(),
  }));
}

/** Mirrors the backend's own invariants (destination required, sum to 100) as a UX nicety —
 * never the authority (CLAUDE.md: the backend always re-validates). */
function describeRowProblems(rows: ItemRow[]): string | null {
  if (rows.length === 0) return "Add at least one destination.";
  for (const r of rows) {
    if (r.mode === "account" && !r.bank_account_id) return "Every row needs a bank account chosen, or switch it to a free-text destination.";
    if (r.mode === "label" && !r.destination_label.trim()) return "Every row needs a destination name, or switch it to a bank account.";
    if (!r.percentage.trim() || Number.isNaN(Number(r.percentage))) return "Every row needs a percentage.";
  }
  const total = runningTotal(rows);
  if (Math.abs(total - 100) > 0.005) {
    return `Percentages must add up to 100%. They currently add up to ${total.toFixed(2)}%.`;
  }
  return null;
}

function accountLabel(a: BankAccountSummary): string {
  return a.account_identifier_last4 ? `${a.account_name} ••${a.account_identifier_last4}` : a.account_name;
}

function ItemRowsEditor({
  rows,
  accounts,
  onChange,
}: {
  rows: ItemRow[];
  accounts: BankAccountSummary[];
  onChange: (rows: ItemRow[]) => void;
}) {
  const total = runningTotal(rows);
  const atTarget = Math.abs(total - 100) < 0.005;

  function updateRow(key: string, patch: Partial<ItemRow>) {
    onChange(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function removeRow(key: string) {
    onChange(rows.filter((r) => r.key !== key));
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.key} className="space-y-2 rounded-md border border-line bg-secondary/40 p-2.5">
            <div className="flex flex-wrap items-center gap-3 text-xs text-ink-soft">
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name={`mode-${row.key}`}
                  checked={row.mode === "account"}
                  onChange={() => updateRow(row.key, { mode: "account" })}
                  className="size-3.5 accent-rust-500"
                />
                Bank account
              </label>
              <label className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name={`mode-${row.key}`}
                  checked={row.mode === "label"}
                  onChange={() => updateRow(row.key, { mode: "label" })}
                  className="size-3.5 accent-rust-500"
                />
                Other destination
              </label>
              <button
                type="button"
                onClick={() => removeRow(row.key)}
                aria-label="Remove this destination"
                className="ml-auto flex size-6 shrink-0 items-center justify-center rounded-full text-ink-faint transition-colors duration-250 ease-ledger hover:bg-overspent-bg hover:text-overspent"
              >
                <XIcon className="size-3.5" aria-hidden />
              </button>
            </div>

            <div className="flex flex-wrap items-start gap-2">
              <div className="min-w-[10rem] flex-1 space-y-1">
                {row.mode === "account" ? (
                  <Select value={row.bank_account_id} onValueChange={(v) => updateRow(row.key, { bank_account_id: v })}>
                    <SelectTrigger className="w-full" aria-label="Bank account">
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
                    aria-label="Destination name"
                    placeholder="e.g. Cash at home"
                    value={row.destination_label}
                    onChange={(e) => updateRow(row.key, { destination_label: e.target.value })}
                  />
                )}
              </div>
              <div className="w-24 space-y-1">
                <div className="relative">
                  <Input
                    aria-label="Percentage"
                    inputMode="decimal"
                    placeholder="0"
                    value={row.percentage}
                    onChange={(e) => updateRow(row.key, { percentage: e.target.value })}
                    className="pr-6"
                  />
                  <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-xs text-ink-faint">
                    %
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between gap-3">
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...rows, blankRow()])}>
          <PlusIcon className="size-3.5" aria-hidden />
          Add destination
        </Button>
        <p className={cn("figure text-sm font-medium", atTarget ? "text-ontrack" : "text-overspent")}>
          {total.toFixed(2)}% of 100%
        </p>
      </div>
    </div>
  );
}

function RuleCreateDialog({ accounts, onCreated }: { accounts: BankAccountSummary[]; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [rows, setRows] = useState<ItemRow[]>([blankRow()]);
  const [problem, setProblem] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setName("");
    setRows([blankRow()]);
    setProblem(null);
    setBanner(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setProblem("Give this rule a name.");
      return;
    }
    const rowProblem = describeRowProblems(rows);
    if (rowProblem) {
      setProblem(rowProblem);
      return;
    }
    setProblem(null);
    setBanner(null);
    setSubmitting(true);
    try {
      await api.savingsDistributionRules.create({ name: name.trim(), items: toPayload(rows) });
      setOpen(false);
      reset();
      onCreated();
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't create this rule. Please try again.");
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
        <Button>New savings rule</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>New savings distribution rule</DialogTitle>
            <DialogDescription>
              Decide how your saved money splits across accounts (or other destinations) — they
              must add up to exactly 100%.
            </DialogDescription>
          </DialogHeader>

          {banner && (
            <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
              {banner}
            </p>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="savings-rule-name">Name</Label>
            <Input id="savings-rule-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. 70/30 split" />
          </div>

          <div className="space-y-1.5">
            <Label>Destinations</Label>
            <ItemRowsEditor rows={rows} accounts={accounts} onChange={setRows} />
            {problem && <p className="text-xs text-overspent">{problem}</p>}
          </div>

          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create rule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RuleEditItemsDialog({
  rule,
  accounts,
  open,
  onOpenChange,
  onSaved,
}: {
  rule: SavingsDistributionRule;
  accounts: BankAccountSummary[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        {open && (
          <RuleEditItemsForm rule={rule} accounts={accounts} onClose={() => onOpenChange(false)} onSaved={onSaved} />
        )}
      </DialogContent>
    </Dialog>
  );
}

function RuleEditItemsForm({
  rule,
  accounts,
  onClose,
  onSaved,
}: {
  rule: SavingsDistributionRule;
  accounts: BankAccountSummary[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [rows, setRows] = useState<ItemRow[]>(() => rule.items.map(rowFromItem));
  const [problem, setProblem] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const rowProblem = describeRowProblems(rows);
    if (rowProblem) {
      setProblem(rowProblem);
      return;
    }
    setProblem(null);
    setBanner(null);
    setSubmitting(true);
    try {
      await api.savingsDistributionRules.replaceItems(rule.id, {
        items: toPayload(rows),
        expected_updated_at: rule.updated_at,
      });
      onClose();
      onSaved();
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't save these destinations.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Edit destinations — {rule.name}</DialogTitle>
      </DialogHeader>
      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}
      <ItemRowsEditor rows={rows} accounts={accounts} onChange={setRows} />
      {problem && <p className="text-xs text-overspent">{problem}</p>}
      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Save destinations"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function DeleteRuleDialog({
  rule,
  open,
  onOpenChange,
  onDeactivated,
}: {
  rule: SavingsDistributionRule;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeactivated: () => void;
}) {
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleConfirm() {
    setSubmitting(true);
    setBanner(null);
    try {
      await api.savingsDistributionRules.update(rule.id, { is_active: false, expected_updated_at: rule.updated_at });
      onOpenChange(false);
      onDeactivated();
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't remove this rule. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove &quot;{rule.name}&quot;?</DialogTitle>
          <DialogDescription>
            This deactivates the rule — it won&apos;t be offered for new allocations, but any
            savings already sent using it keep their history.
          </DialogDescription>
        </DialogHeader>
        {banner && (
          <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
            {banner}
          </p>
        )}
        <DialogFooter>
          <Button variant="destructive" onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Removing…" : "Remove rule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RuleCard({
  rule,
  accounts,
  onChanged,
}: {
  rule: SavingsDistributionRule;
  accounts: BankAccountSummary[];
  onChanged: () => void;
}) {
  const [editingItems, setEditingItems] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const accountsById = new Map(accounts.map((a) => [a.id, a]));
  const total = rule.items.reduce((sum, i) => sum + Number(i.percentage), 0);

  return (
    <div className="rounded-md border border-line bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-display text-lg text-ink">{rule.name}</h3>
          {rule.is_default && <StatusBadge status="AUTO" />}
        </div>
        <div className="flex gap-3 text-sm font-medium">
          <button type="button" onClick={() => setEditingItems(true)} className="text-rust-500 hover:text-rust-700">
            Edit destinations
          </button>
          <button type="button" onClick={() => setDeleting(true)} className="text-overspent hover:text-overspent/80">
            Remove
          </button>
        </div>
      </div>

      <ul className="mt-3 divide-y divide-line">
        {rule.items.map((item) => {
          const account = item.bank_account_id ? accountsById.get(item.bank_account_id) : undefined;
          return (
            <li key={item.id} className="flex items-center justify-between gap-3 py-1.5 text-sm">
              <span className="text-ink">{account ? accountLabel(account) : item.destination_label}</span>
              <span className="figure text-ink-soft">{Number(item.percentage).toFixed(2)}%</span>
            </li>
          );
        })}
      </ul>
      <p className={cn("mt-2 text-right text-xs figure", Math.abs(total - 100) < 0.005 ? "text-ink-faint" : "text-overspent")}>
        {total.toFixed(2)}% total
      </p>

      <RuleEditItemsDialog rule={rule} accounts={accounts} open={editingItems} onOpenChange={setEditingItems} onSaved={onChanged} />
      <DeleteRuleDialog rule={rule} open={deleting} onOpenChange={setDeleting} onDeactivated={onChanged} />
    </div>
  );
}

export function SavingsDistributionRulesManager({
  accounts,
  onRulesChanged,
}: {
  accounts: BankAccountSummary[];
  onRulesChanged?: () => void;
}) {
  const [rules, setRules] = useState<SavingsDistributionRule[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.savingsDistributionRules.list({ is_active: true, page_size: 100 });
      setRules(res.data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your savings distribution rules.");
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  function handleChanged() {
    void load();
    onRulesChanged?.();
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <RuleCreateDialog accounts={accounts} onCreated={handleChanged} />
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {!error && rules === null && (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-md bg-secondary" />
          ))}
        </div>
      )}

      {!error && rules !== null && rules.length === 0 && (
        <EmptyState
          title="No savings distribution rules yet"
          message="Create one to automatically split your final savings across accounts each period."
          action={<RuleCreateDialog accounts={accounts} onCreated={handleChanged} />}
        />
      )}

      {!error && rules !== null && rules.length > 0 && (
        <div className="space-y-4">
          {rules.map((rule) => (
            <RuleCard key={rule.id} rule={rule} accounts={accounts} onChanged={handleChanged} />
          ))}
        </div>
      )}
    </div>
  );
}
