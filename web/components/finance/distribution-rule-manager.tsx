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
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { StatusBadge } from "./status-badge";
import { api, ApiError } from "@/lib/api";
import type { DistributionCategoryInput } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { DistributionRule, DistributionRuleCategory } from "@/lib/types";

/**
 * Rule *management* — create a `DistributionRule`, edit its own fields, and
 * replace its category set (spec §12: name/percentage/flags, no computed
 * amounts here — that's `GET /distributions/{period_id}`, rendered by the
 * "This period" tab in app/(app)/distribution/page.tsx, not this file).
 *
 * Deliberately not built on `MoneyInManager`: that component's shape is "one
 * flat form for one flat record." A rule is a record *with a nested,
 * dynamic-length, sum-must-equal-100 collection* — forcing that through a
 * single-level field list would either drop the running-total UX or bolt on
 * a special case `MoneyInManager` has no business knowing about. The
 * closed/delete-confirmation *feel* (banner errors, plain-language field
 * errors, disabled state while submitting) is kept consistent by hand rather
 * than shared code, since there's no closed-period concept for a rule itself.
 */

interface CategoryRow {
  /** Stable React key only — never sent to the backend. Existing categories
   * key off their real id; new rows get a locally-generated one. */
  key: string;
  id?: string;
  name: string;
  percentage: string;
  contributes_to_automatic_savings: boolean;
  is_unallocated_bucket: boolean;
}

let rowSeq = 0;
function blankRow(): CategoryRow {
  rowSeq += 1;
  return {
    key: `new-${rowSeq}`,
    name: "",
    percentage: "",
    contributes_to_automatic_savings: true,
    is_unallocated_bucket: false,
  };
}

function rowFromCategory(c: DistributionRuleCategory): CategoryRow {
  return {
    key: c.id,
    id: c.id,
    name: c.name,
    percentage: String(Number(c.percentage)),
    contributes_to_automatic_savings: c.contributes_to_automatic_savings,
    is_unallocated_bucket: c.is_unallocated_bucket,
  };
}

function runningTotal(rows: CategoryRow[]): number {
  return rows.reduce((sum, r) => sum + (Number(r.percentage) || 0), 0);
}

function toPayload(rows: CategoryRow[]): DistributionCategoryInput[] {
  return rows.map((r, i) => ({
    id: r.id,
    name: r.name.trim(),
    percentage: r.percentage.trim(),
    contributes_to_automatic_savings: r.contributes_to_automatic_savings,
    is_unallocated_bucket: r.is_unallocated_bucket,
    display_order: i,
  }));
}

/** Plain-language client-side check mirroring the backend's own invariant
 * (D-009/D-010) — a UX nicety that blocks an obviously-invalid submit before
 * a round trip, never the actual authority (CLAUDE.md: the backend always
 * re-validates and is the only source of truth for whether 100% was hit). */
function describeRowProblems(rows: CategoryRow[]): string | null {
  if (rows.length === 0) return "Add at least one category.";
  if (rows.some((r) => !r.name.trim())) return "Every category needs a name.";
  if (rows.some((r) => !r.percentage.trim() || Number.isNaN(Number(r.percentage)))) {
    return "Every category needs a percentage.";
  }
  if (rows.filter((r) => r.is_unallocated_bucket).length > 1) {
    return "Only one category can be the unallocated bucket.";
  }
  const total = runningTotal(rows);
  if (Math.abs(total - 100) > 0.005) {
    return `Percentages must add up to 100%. They currently add up to ${total.toFixed(2)}%.`;
  }
  return null;
}

function CategoryRowsEditor({
  rows,
  onChange,
}: {
  rows: CategoryRow[];
  onChange: (rows: CategoryRow[]) => void;
}) {
  const total = runningTotal(rows);
  const atTarget = Math.abs(total - 100) < 0.005;

  function updateRow(key: string, patch: Partial<CategoryRow>) {
    onChange(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function removeRow(key: string) {
    onChange(rows.filter((r) => r.key !== key));
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.key} className="flex flex-wrap items-start gap-2 rounded-md border border-line bg-secondary/40 p-2.5">
            <div className="min-w-[8rem] flex-1 space-y-1">
              <Input
                aria-label="Category name"
                placeholder="e.g. Needs"
                value={row.name}
                onChange={(e) => updateRow(row.key, { name: e.target.value })}
              />
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
            <label className="flex items-center gap-1.5 pt-1.5 text-xs text-ink-soft">
              <input
                type="checkbox"
                checked={row.contributes_to_automatic_savings}
                onChange={(e) => updateRow(row.key, { contributes_to_automatic_savings: e.target.checked })}
                className="size-3.5 rounded border-line accent-rust-500"
              />
              Feeds savings
            </label>
            <label className="flex items-center gap-1.5 pt-1.5 text-xs text-ink-soft">
              <input
                type="checkbox"
                checked={row.is_unallocated_bucket}
                onChange={(e) => updateRow(row.key, { is_unallocated_bucket: e.target.checked })}
                className="size-3.5 rounded border-line accent-rust-500"
              />
              Unallocated
            </label>
            <button
              type="button"
              onClick={() => removeRow(row.key)}
              aria-label={`Remove ${row.name || "this category"}`}
              className="ml-auto flex size-6 shrink-0 items-center justify-center rounded-full text-ink-faint transition-colors duration-250 ease-ledger hover:bg-overspent-bg hover:text-overspent"
            >
              <XIcon className="size-3.5" aria-hidden />
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between gap-3">
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...rows, blankRow()])}>
          <PlusIcon className="size-3.5" aria-hidden />
          Add category
        </Button>
        <p
          className={cn(
            "figure text-sm font-medium",
            atTarget ? "text-ontrack" : "text-overspent",
          )}
        >
          {total.toFixed(2)}% of 100%
        </p>
      </div>
    </div>
  );
}

function RuleCreateDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [rows, setRows] = useState<CategoryRow[]>([blankRow()]);
  const [problem, setProblem] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setName("");
    setDescription("");
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
      await api.distributionRules.create({
        name: name.trim(),
        description: description.trim() || null,
        categories: toPayload(rows),
      });
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
        <Button>New rule</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>New distribution rule</DialogTitle>
            <DialogDescription>
              Split your income into categories — they must add up to exactly 100% (add an
              &quot;Unallocated&quot; category if you don&apos;t want to plan every dalasi).
            </DialogDescription>
          </DialogHeader>

          {banner && (
            <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
              {banner}
            </p>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="rule-name">Name</Label>
            <Input id="rule-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. My 50/30/20" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="rule-description">Description</Label>
            <textarea
              id="rule-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Optional"
              className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm text-ink outline-none focus-visible:border-rust-500"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Categories</Label>
            <CategoryRowsEditor rows={rows} onChange={setRows} />
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

function RuleEditDetailsDialog({
  rule,
  open,
  onOpenChange,
  onSaved,
}: {
  rule: DistributionRule;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {/* Mounted fresh each time the dialog opens (same convention as
            MoneyInManager's edit dialog) so its form state always starts from
            this rule's current values — no reset-on-open effect needed. */}
        {open && (
          <RuleEditDetailsForm
            rule={rule}
            onClose={() => onOpenChange(false)}
            onSaved={onSaved}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function RuleEditDetailsForm({
  rule,
  onClose,
  onSaved,
}: {
  rule: DistributionRule;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(rule.name);
  const [description, setDescription] = useState(rule.description ?? "");
  const [isDefault, setIsDefault] = useState(rule.is_default);
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setBanner("Give this rule a name.");
      return;
    }
    setSubmitting(true);
    setBanner(null);
    try {
      await api.distributionRules.update(rule.id, {
        name: name.trim(),
        description: description.trim() || null,
        is_default: isDefault,
        expected_updated_at: rule.updated_at,
      });
      onClose();
      onSaved();
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't save these changes.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Edit rule details</DialogTitle>
      </DialogHeader>
      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}
      <div className="space-y-1.5">
        <Label htmlFor="edit-rule-name">Name</Label>
        <Input id="edit-rule-name" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="edit-rule-description">Description</Label>
        <textarea
          id="edit-rule-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm text-ink outline-none focus-visible:border-rust-500"
        />
      </div>
      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          checked={isDefault}
          onChange={(e) => setIsDefault(e.target.checked)}
          className="size-4 rounded border-line accent-rust-500"
        />
        Use this rule by default for new periods
      </label>
      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Save changes"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function RuleEditCategoriesDialog({
  rule,
  open,
  onOpenChange,
  onSaved,
}: {
  rule: DistributionRule;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        {open && (
          <RuleEditCategoriesForm
            rule={rule}
            onClose={() => onOpenChange(false)}
            onSaved={onSaved}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function RuleEditCategoriesForm({
  rule,
  onClose,
  onSaved,
}: {
  rule: DistributionRule;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [rows, setRows] = useState<CategoryRow[]>(() => rule.categories.map(rowFromCategory));
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
      await api.distributionRules.replaceCategories(rule.id, {
        categories: toPayload(rows),
        expected_updated_at: rule.updated_at,
      });
      onClose();
      onSaved();
    } catch (err) {
      setBanner(err instanceof ApiError ? err.message : "Couldn't save these categories.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Edit categories — {rule.name}</DialogTitle>
        <DialogDescription>
          Existing categories keep their history when you rename or adjust them; removing one
          here removes it from this rule going forward.
        </DialogDescription>
      </DialogHeader>
      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}
      <CategoryRowsEditor rows={rows} onChange={setRows} />
      {problem && <p className="text-xs text-overspent">{problem}</p>}
      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Save categories"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function DeleteRuleDialog({
  rule,
  open,
  onOpenChange,
  onDeleted,
}: {
  rule: DistributionRule;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && (
          <DeleteRuleConfirm
            rule={rule}
            onClose={() => onOpenChange(false)}
            onDeleted={onDeleted}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function DeleteRuleConfirm({
  rule,
  onClose,
  onDeleted,
}: {
  rule: DistributionRule;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleConfirm() {
    setSubmitting(true);
    setBanner(null);
    try {
      await api.distributionRules.remove(rule.id);
      onClose();
      onDeleted();
    } catch (err) {
      setBanner(
        err instanceof ApiError
          ? err.message
          : "Couldn't remove this rule. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Remove &quot;{rule.name}&quot;?</DialogTitle>
        <DialogDescription>
          This deactivates the rule — it won&apos;t be offered for new periods, but past periods
          that used it keep their history. It can&apos;t be removed while it&apos;s the active rule
          for an open period.
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
    </>
  );
}

function RuleCard({ rule, onChanged }: { rule: DistributionRule; onChanged: () => void }) {
  const [editingDetails, setEditingDetails] = useState(false);
  const [editingCategories, setEditingCategories] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const total = rule.categories.reduce((sum, c) => sum + Number(c.percentage), 0);

  return (
    <div className="rounded-md border border-line bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-lg text-ink">{rule.name}</h3>
            {rule.is_default && <StatusBadge status="AUTO" />}
          </div>
          {rule.description && <p className="mt-0.5 text-sm text-ink-soft">{rule.description}</p>}
        </div>
        <div className="flex gap-3 text-sm font-medium">
          <button type="button" onClick={() => setEditingDetails(true)} className="text-rust-500 hover:text-rust-700">
            Edit details
          </button>
          <button type="button" onClick={() => setEditingCategories(true)} className="text-rust-500 hover:text-rust-700">
            Edit categories
          </button>
          <button type="button" onClick={() => setDeleting(true)} className="text-overspent hover:text-overspent/80">
            Remove
          </button>
        </div>
      </div>

      <ul className="mt-3 divide-y divide-line">
        {rule.categories
          .slice()
          .sort((a, b) => a.display_order - b.display_order)
          .map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-3 py-1.5 text-sm">
              <span className="flex items-center gap-2 text-ink">
                {c.name}
                {c.is_unallocated_bucket && <StatusBadge status="UNALLOCATED" />}
                {c.contributes_to_automatic_savings && (
                  <span className="text-[0.6875rem] tracking-wideish text-ink-faint uppercase">feeds savings</span>
                )}
              </span>
              <span className="figure text-ink-soft">{Number(c.percentage).toFixed(2)}%</span>
            </li>
          ))}
      </ul>
      <p className={cn("mt-2 text-right text-xs figure", Math.abs(total - 100) < 0.005 ? "text-ink-faint" : "text-overspent")}>
        {total.toFixed(2)}% total
      </p>

      <RuleEditDetailsDialog rule={rule} open={editingDetails} onOpenChange={setEditingDetails} onSaved={onChanged} />
      <RuleEditCategoriesDialog rule={rule} open={editingCategories} onOpenChange={setEditingCategories} onSaved={onChanged} />
      <DeleteRuleDialog rule={rule} open={deleting} onOpenChange={setDeleting} onDeleted={onChanged} />
    </div>
  );
}

export function DistributionRulesManager({ onRulesChanged }: { onRulesChanged?: () => void }) {
  const [rules, setRules] = useState<DistributionRule[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.distributionRules.list({ is_active: true, page_size: 100 });
      setRules(res.data);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Couldn't load your distribution rules.",
      );
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
        <RuleCreateDialog onCreated={handleChanged} />
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {!error && rules === null && (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-md bg-secondary" />
          ))}
        </div>
      )}

      {!error && rules !== null && rules.length === 0 && (
        <EmptyState
          title="No distribution rules yet"
          message="Create a rule — like a 50/30/20 split — to decide what share of your income goes where each month."
          action={<RuleCreateDialog onCreated={handleChanged} />}
        />
      )}

      {!error && rules !== null && rules.length > 0 && (
        <div className="space-y-4">
          {rules.map((rule) => (
            <RuleCard key={rule.id} rule={rule} onChanged={handleChanged} />
          ))}
        </div>
      )}
    </div>
  );
}
