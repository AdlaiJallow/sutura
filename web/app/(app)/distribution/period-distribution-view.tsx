"use client";

import { useState, type FormEvent } from "react";
import { AmountDisplay } from "@/components/finance/amount-display";
import { CategoryProgressBar } from "@/components/finance/category-progress-bar";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { api, ApiError } from "@/lib/api";
import { monthLabel } from "@/lib/text";
import type { DistributionRule, DistributionView, FinancialPeriod } from "@/lib/types";

/**
 * Pure presentational half of the "This period" tab — separated from
 * app/(app)/distribution/page.tsx (which owns the actual `usePeriod` /
 * `useDistributionView` data fetching) the same way dashboard-view.tsx is
 * split from dashboard/page.tsx, so it can be unit-tested with plain fixture
 * props instead of mocking hooks (see period-distribution-view.test.tsx: a
 * normal on-track case and an overspent one, per spec §38/§13 — overspending
 * must render as a plain negative "Remaining," never hidden or clamped).
 */
export function PeriodDistributionView({
  period,
  view,
  error,
  loading,
  onReload,
  rules,
  rulesError,
  onRuleApplied,
  onCreateRule,
}: {
  period: FinancialPeriod;
  view: DistributionView | null;
  error: string | null;
  loading: boolean;
  onReload: () => void;
  rules: DistributionRule[] | null;
  rulesError: string | null;
  onRuleApplied: () => void;
  onCreateRule: () => void;
}) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-28 animate-pulse rounded-md bg-secondary" />
        ))}
      </div>
    );
  }

  if (error || !view) {
    return <ErrorState message={error ?? undefined} onRetry={onReload} />;
  }

  const currency = period.base_currency;
  const isClosed = period.status === "CLOSED";

  if (view.distribution_rule_id === null) {
    return (
      <div className="space-y-4">
        {rules === null && !rulesError && (
          <div className="h-24 animate-pulse rounded-md bg-secondary" />
        )}
        {rulesError && <ErrorState message={rulesError} />}
        {rules !== null && (
          <EmptyState
            title="No distribution rule selected yet"
            message={
              rules.length > 0
                ? `Choose a rule for ${monthLabel(period.year, period.month)} so income can be split into categories.`
                : `You don't have any distribution rules yet. Create one — like a 50/30/20 split — to start planning ${monthLabel(period.year, period.month)}.`
            }
            action={
              rules.length > 0 ? (
                <SelectRuleForm
                  period={period}
                  rules={rules}
                  currentRuleId={null}
                  onApplied={onRuleApplied}
                />
              ) : (
                <Button onClick={onCreateRule}>Create a distribution rule</Button>
              )
            }
          />
        )}
        <IncomeNote totalMonthlyIncome={view.total_monthly_income} currency={currency} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-md border border-line bg-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[0.6875rem] font-medium tracking-wideish text-ink-faint uppercase">
              Active rule
            </p>
            <p className="mt-0.5 font-display text-lg text-ink">{view.distribution_rule_name}</p>
          </div>
          {isClosed ? (
            <p className="max-w-xs text-xs text-ink-soft">
              This period is closed, so its distribution rule can&apos;t be changed here.
            </p>
          ) : rules !== null ? (
            <SelectRuleForm
              period={period}
              rules={rules}
              currentRuleId={view.distribution_rule_id}
              onApplied={onRuleApplied}
              compact
            />
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-4">
        <Stat label="Money Available" value={view.total_monthly_income} currency={currency} emphasize />
        <Stat label="Planned" value={view.total_allocation} currency={currency} />
        <Stat label="Spent" value={view.total_used} currency={currency} />
        <Stat label="Remaining" value={view.total_remaining} currency={currency} tone="auto" />
      </div>

      {view.categories.length === 0 ? (
        <EmptyState title="This rule has no categories" message="Edit it under Manage rules to add some." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {view.categories.map((category) => (
            <CategoryProgressBar key={category.id} category={category} currency={currency} />
          ))}
        </div>
      )}
    </div>
  );
}

function IncomeNote({ totalMonthlyIncome, currency }: { totalMonthlyIncome: string; currency: string }) {
  return (
    <p className="text-sm text-ink-soft">
      Money available so far this period:{" "}
      <AmountDisplay value={totalMonthlyIncome} currency={currency} size="sm" weight="semibold" />
    </p>
  );
}

function SelectRuleForm({
  period,
  rules,
  currentRuleId,
  onApplied,
  compact = false,
}: {
  period: FinancialPeriod;
  rules: DistributionRule[];
  currentRuleId: string | null;
  onApplied: () => void;
  compact?: boolean;
}) {
  const [ruleId, setRuleId] = useState(currentRuleId ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!ruleId) {
      setError("Choose a rule first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.financialPeriods.selectDistributionRule(period.id, { distribution_rule_id: ruleId });
      onApplied();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't apply this rule.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className={compact ? "flex items-start gap-2" : "flex flex-col items-center gap-2"}>
      <div className="flex items-center gap-2">
        <Select value={ruleId} onValueChange={setRuleId}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Choose a rule" />
          </SelectTrigger>
          <SelectContent>
            {rules.map((rule) => (
              <SelectItem key={rule.id} value={rule.id}>
                {rule.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button type="submit" disabled={submitting || ruleId === currentRuleId}>
          {submitting ? "Applying…" : currentRuleId ? "Switch" : "Apply"}
        </Button>
      </div>
      {error && <p className="text-xs text-overspent">{error}</p>}
    </form>
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
