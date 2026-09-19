"use client";

import { useCallback, useEffect, useState } from "react";
import {
  defaultDateReceived,
  MoneyInManager,
  type MoneyInField,
  type MoneyInFormValues,
} from "@/components/finance/money-in-manager";
import { SavingsAllocationManager } from "@/components/finance/savings-allocation-manager";
import { SavingsDistributionRulesManager } from "@/components/finance/savings-distribution-rule-manager";
import { SavingsRollup } from "@/components/finance/savings-rollup";
import { AmountDisplay } from "@/components/finance/amount-display";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState } from "@/components/layout/error-state";
import { usePeriod } from "@/components/layout/period-context";
import { api, ApiError } from "@/lib/api";
import { formatLedgerDate } from "@/lib/money";
import { monthLabel } from "@/lib/text";
import { useMoneyInList } from "@/lib/use-money-in-list";
import { useSavingsSummary } from "@/lib/use-savings-summary";
import type { BankAccountSummary, SavingsDistributionRule, SavingsItem } from "@/lib/types";

const SAVINGS_ITEM_FIELDS: MoneyInField[] = [
  { name: "name", label: "Name", type: "text", required: true, placeholder: "e.g. Emergency fund top-up" },
  { name: "amount", label: "Amount", type: "amount", required: true, placeholder: "e.g. 1000" },
  { name: "currency", label: "Currency", type: "currency", required: true },
  { name: "date", label: "Date", type: "date", required: true },
  { name: "destination", label: "Where it's going", type: "text", placeholder: "Optional — e.g. Savings Vault" },
  { name: "notes", label: "Notes", type: "textarea", placeholder: "Optional" },
];

/**
 * Ties together the three savings pieces (spec §32/task brief): the live
 * Automatic/Manual/Final/Distributed/Undistributed rollup (`SavingsRollup`,
 * from `GET /savings/{period_id}`), manual savings entries (a plain
 * `MoneyInManager` list, same shape as allowances/income), and where that
 * money actually goes — either by rule (`SavingsDistributionRulesManager` +
 * "Apply rule") or by hand (`SavingsAllocationManager`'s manual dialog).
 */
export default function SavingsPage() {
  const { period } = usePeriod();
  const currency = period.base_currency;
  const label = monthLabel(period.year, period.month);
  const [tab, setTab] = useState<"overview" | "rules">("overview");

  const { summary, error: summaryError, loading: summaryLoading, reload: reloadSummary } = useSavingsSummary(period.id);

  const fetchItems = useCallback(
    () => api.savingsItems.list({ financial_period_id: period.id, page_size: 100 }),
    [period.id],
  );
  const { records: items, error: itemsError, reload: reloadItems } = useMoneyInList(fetchItems);

  const [accounts, setAccounts] = useState<BankAccountSummary[]>([]);
  const [rules, setRules] = useState<SavingsDistributionRule[] | null>(null);
  const [rulesError, setRulesError] = useState<string | null>(null);

  const loadAccounts = useCallback(async () => {
    try {
      const res = await api.bankAccounts.list({ is_active: true, page_size: 100 });
      setAccounts(res.data);
    } catch {
      // Best-effort — the destination pickers simply offer nothing rather than blocking the
      // rest of the page (same convention as the Expenses page's "Paid from" field).
      setAccounts([]);
    }
  }, []);

  const loadRules = useCallback(async () => {
    setRulesError(null);
    try {
      const res = await api.savingsDistributionRules.list({ is_active: true, page_size: 100 });
      setRules(res.data);
    } catch (err) {
      setRulesError(err instanceof ApiError ? err.message : "Couldn't load your savings distribution rules.");
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await Promise.all([loadAccounts(), loadRules()]);
    })();
  }, [loadAccounts, loadRules]);

  // Manual items and allocations both change the numbers `SavingsRollup` shows, but that rollup
  // is a cached row only refreshed by a summary recalculation (see `use-savings-summary.ts`) —
  // every mutation on this page reloads it alongside its own list.
  async function afterItemsChanged() {
    reloadItems();
    await reloadSummary();
  }

  async function afterAllocationsChanged() {
    await reloadSummary();
  }

  if (summaryLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-md bg-secondary" />
        <div className="h-28 animate-pulse rounded-md bg-secondary" />
      </div>
    );
  }

  if (summaryError || !summary) {
    return <ErrorState message={summaryError ?? undefined} onRetry={reloadSummary} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Savings</h1>
        <p className="mt-1 max-w-lg text-sm text-ink-soft">
          What you&apos;ve saved automatically and by hand in {label}, and where it&apos;s been sent.
        </p>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "overview" | "rules")}>
        <TabsList variant="line">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="rules">Distribution rules</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6 space-y-8">
          <SavingsRollup summary={summary} currency={currency} />

          <section className="space-y-3">
            <h2 className="font-display text-xl text-ink">Manual savings</h2>
            {itemsError && <ErrorState message={itemsError} onRetry={reloadItems} />}
            {!itemsError && (
              <MoneyInManager<SavingsItem>
                period={period}
                fields={SAVINGS_ITEM_FIELDS}
                addLabel="Add manual saving"
                singularLabel="savings entry"
                emptyTitle="No manual savings yet"
                emptyMessage={`Add anything you saved by hand in ${label} — beyond what's saved automatically from unused budget.`}
                records={items}
                error={null}
                onReload={afterItemsChanged}
                describeRecord={(i) => i.name}
                defaultValues={() => ({
                  name: "",
                  amount: "",
                  currency,
                  date: defaultDateReceived(),
                  destination: "",
                  notes: "",
                })}
                valuesFromRecord={(i) => ({
                  name: i.name,
                  amount: String(Number(i.amount)),
                  currency: i.currency,
                  date: i.date,
                  destination: i.destination ?? "",
                  notes: i.notes ?? "",
                })}
                onCreate={async (values: MoneyInFormValues) =>
                  api.savingsItems.create({
                    financial_period_id: period.id,
                    name: values.name as string,
                    amount: values.amount as string,
                    currency: values.currency as string,
                    date: values.date as string,
                    destination: (values.destination as string | null) || null,
                    notes: (values.notes as string | null) ?? null,
                  })
                }
                onUpdate={async (id, values, expectedUpdatedAt) =>
                  api.savingsItems.update(id, {
                    name: values.name as string,
                    amount: values.amount as string,
                    currency: values.currency as string,
                    date: values.date as string,
                    destination: (values.destination as string | null) || null,
                    notes: (values.notes as string | null) ?? null,
                    expected_updated_at: expectedUpdatedAt,
                  })
                }
                onDelete={(id) => api.savingsItems.remove(id)}
                columns={[
                  { header: "Name", render: (i) => <span className="text-ink">{i.name}</span> },
                  {
                    header: "Amount",
                    className: "text-right",
                    render: (i) => <AmountDisplay value={i.amount} currency={i.currency} />,
                  },
                  { header: "Date", className: "figure text-xs text-ink-faint", render: (i) => formatLedgerDate(i.date) },
                  {
                    header: "Destination",
                    className: "text-xs text-ink-faint",
                    render: (i) => i.destination ?? "—",
                  },
                ]}
              />
            )}
          </section>

          <section className="space-y-3">
            <h2 className="font-display text-xl text-ink">Send savings to accounts</h2>
            {rulesError && <ErrorState message={rulesError} onRetry={loadRules} />}
            {!rulesError && (
              <SavingsAllocationManager
                period={period}
                accounts={accounts}
                rules={rules ?? []}
                onAllocated={afterAllocationsChanged}
              />
            )}
          </section>
        </TabsContent>

        <TabsContent value="rules" className="mt-6">
          <SavingsDistributionRulesManager accounts={accounts} onRulesChanged={loadRules} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
