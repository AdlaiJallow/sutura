"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AmountDisplay } from "@/components/finance/amount-display";
import {
  defaultDateReceived,
  MoneyInManager,
  type MoneyInFormValues,
} from "@/components/finance/money-in-manager";
import { buildExpenseFields } from "@/components/finance/expense-fields";
import { ErrorState } from "@/components/layout/error-state";
import { usePeriod } from "@/components/layout/period-context";
import { api } from "@/lib/api";
import { formatLedgerDate } from "@/lib/money";
import { humanizeEnum, monthLabel } from "@/lib/text";
import { useDistributionView } from "@/lib/use-distribution-view";
import { useMoneyInList } from "@/lib/use-money-in-list";
import type { BankAccountSummary, Expense, ExpenseCategory, PaymentMethod } from "@/lib/types";

/**
 * Every expense, always linked to a distribution category once the period
 * has one selected (D-006 — enforced server-side, mirrored here only as a
 * UX nicety: the category select is populated from the period's *actual*
 * categories via `GET /distributions/{period_id}`, never free text, and the
 * field itself only appears/becomes required once a rule exists — spec §32).
 *
 * Built on `MoneyInManager` rather than a parallel table+dialog+delete-
 * confirmation implementation: expenses are structurally the same
 * "period-scoped list with a form" shape as salary/allowances/income, just
 * with more enum-heavy fields and one relational one. The relational field's
 * *options* are computed here (from the distribution view + bank accounts)
 * and handed to the generic `select` field type the manager already
 * supports — no changes needed to the shared component (CLAUDE.md: reuse
 * over reinventing the same pattern a third time).
 */
export default function ExpensesPage() {
  const { period } = usePeriod();
  const currency = period.base_currency;

  const { view, error: viewError, loading: viewLoading, reload: reloadView } = useDistributionView(period.id);
  const [bankAccounts, setBankAccounts] = useState<BankAccountSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await api.bankAccounts.list({ is_active: true, page_size: 100 });
        if (!cancelled) setBankAccounts(res.data);
      } catch {
        // Best-effort: bank accounts isn't a fully built module yet (task brief).
        // "Paid from" simply offers nothing rather than blocking expense entry —
        // never a fabricated or cached list standing in for the real one.
        if (!cancelled) setBankAccounts([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [period.id]);

  const fetchExpenses = useCallback(
    () => api.expenses.list({ financial_period_id: period.id, page_size: 100 }),
    [period.id],
  );
  const { records, error, reload } = useMoneyInList(fetchExpenses);

  const categories = useMemo(() => view?.categories ?? [], [view]);
  const categoryRequired = categories.length > 0;

  const categoryName = useMemo(() => {
    const map = new Map(categories.map((c) => [c.id, c.name]));
    return (id: string | null) => (id ? (map.get(id) ?? "Unknown category") : "—");
  }, [categories]);

  const fields = useMemo(
    () => buildExpenseFields(categories, bankAccounts),
    [categories, bankAccounts],
  );

  if (viewLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-md bg-secondary" />
        <div className="h-40 animate-pulse rounded-md bg-secondary" />
      </div>
    );
  }

  if (viewError) {
    return <ErrorState message={viewError} onRetry={reloadView} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Expenses</h1>
        <p className="mt-1 max-w-lg text-sm text-ink-soft">
          Everything you spent in {monthLabel(period.year, period.month)}
          {categoryRequired ? ", linked to a budget category so overspending shows up right away." : "."}
        </p>
        {!categoryRequired && (
          <p className="mt-3 rounded-md border border-line bg-secondary px-4 py-3 text-sm text-ink-soft">
            No distribution rule is selected for this period yet, so expenses can&apos;t be linked to
            a budget category.{" "}
            <a href="/distribution" className="font-medium text-rust-500 hover:text-rust-700">
              Select one
            </a>{" "}
            to see spending against your plan.
          </p>
        )}
      </div>

      <MoneyInManager<Expense>
        period={period}
        fields={fields}
        addLabel="Add expense"
        singularLabel="expense"
        emptyTitle="No expenses yet"
        emptyMessage={`Add what you spent in ${monthLabel(period.year, period.month)} to see it against your plan.`}
        records={records}
        error={error}
        onReload={reload}
        describeRecord={(e) => e.name}
        defaultValues={() => ({
          name: "",
          expense_category: "",
          distribution_category_id: "",
          amount: "",
          currency,
          expense_date: defaultDateReceived(),
          payment_method: "",
          bank_account_id: "",
          notes: "",
        })}
        valuesFromRecord={(e) => ({
          name: e.name,
          expense_category: e.expense_category,
          distribution_category_id: e.distribution_category_id ?? "",
          amount: String(Number(e.amount)),
          currency: e.currency,
          expense_date: e.expense_date,
          payment_method: e.payment_method ?? "",
          bank_account_id: e.bank_account_id ?? "",
          notes: e.notes ?? "",
        })}
        onCreate={async (values: MoneyInFormValues) =>
          api.expenses.create({
            financial_period_id: period.id,
            distribution_category_id: (values.distribution_category_id as string | null) || null,
            name: values.name as string,
            expense_category: values.expense_category as ExpenseCategory,
            amount: values.amount as string,
            currency: values.currency as string,
            expense_date: values.expense_date as string,
            payment_method: (values.payment_method as PaymentMethod | null) || null,
            bank_account_id: (values.bank_account_id as string | null) || null,
            notes: (values.notes as string | null) ?? null,
          })
        }
        onUpdate={async (id, values, expectedUpdatedAt) =>
          api.expenses.update(id, {
            distribution_category_id: (values.distribution_category_id as string | null) || null,
            name: values.name as string,
            expense_category: values.expense_category as ExpenseCategory,
            amount: values.amount as string,
            currency: values.currency as string,
            expense_date: values.expense_date as string,
            payment_method: (values.payment_method as PaymentMethod | null) || null,
            bank_account_id: (values.bank_account_id as string | null) || null,
            notes: (values.notes as string | null) ?? null,
            expected_updated_at: expectedUpdatedAt,
          })
        }
        onDelete={(id) => api.expenses.remove(id)}
        columns={[
          { header: "Name", render: (e) => <span className="text-ink">{e.name}</span> },
          {
            header: "Category",
            className: "text-xs text-ink-faint",
            render: (e) => humanizeEnum(e.expense_category),
          },
          {
            header: "Budget category",
            className: "text-xs text-ink-faint",
            render: (e) => categoryName(e.distribution_category_id),
          },
          {
            header: "Amount",
            className: "text-right",
            render: (e) => <AmountDisplay value={e.amount} currency={e.currency} />,
          },
          {
            header: "Date",
            className: "figure text-xs text-ink-faint",
            render: (e) => formatLedgerDate(e.expense_date),
          },
          {
            header: "Paid via",
            className: "text-xs text-ink-faint",
            render: (e) => (e.payment_method ? humanizeEnum(e.payment_method) : "—"),
          },
        ]}
      />
    </div>
  );
}
