"use client";

import { useCallback } from "react";
import { AmountDisplay } from "@/components/finance/amount-display";
import { MoneyInManager, type MoneyInField, type MoneyInFormValues } from "@/components/finance/money-in-manager";
import { usePeriod } from "@/components/layout/period-context";
import { api } from "@/lib/api";
import { humanizeEnum, monthLabel } from "@/lib/text";
import { useMoneyInList } from "@/lib/use-money-in-list";
import type { Salary, SalaryStatus } from "@/lib/types";

const FIELDS: MoneyInField[] = [
  { name: "net_amount", label: "Net amount", type: "amount", required: true, placeholder: "e.g. 38500" },
  { name: "currency", label: "Currency", type: "currency", required: true },
  {
    name: "status",
    label: "Status",
    type: "select",
    required: true,
    options: [
      { value: "RECEIVED", label: "Received" },
      { value: "EXPECTED", label: "Expected" },
    ],
  },
  { name: "notes", label: "Notes", type: "textarea", placeholder: "Optional" },
];

/**
 * Salary is one record per period (D-008), so this page is really "set your
 * salary for this period" — but it's built on the same list+dialog manager
 * every money-in page uses (`maxRecords={1}` just hides Add once a row
 * exists), rather than a bespoke single-record form.
 */
export default function SalaryPage() {
  const { period } = usePeriod();
  const currency = period.base_currency;

  const fetchList = useCallback(() => api.salaries.list({ financial_period_id: period.id }), [period.id]);
  const { records, error, reload } = useMoneyInList(fetchList);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Salary</h1>
        <p className="mt-1 max-w-md text-sm text-ink-soft">
          Your net salary for {monthLabel(period.year, period.month)} — one entry per period, feeding
          straight into your total income.
        </p>
      </div>

      <MoneyInManager<Salary>
        period={period}
        fields={FIELDS}
        maxRecords={1}
        addLabel="Add salary"
        singularLabel="salary record"
        emptyTitle="No salary recorded yet"
        emptyMessage={`Add your net salary for ${monthLabel(period.year, period.month)} to include it in this month's income.`}
        records={records}
        error={error}
        onReload={reload}
        describeRecord={(s) => `Salary of ${s.net_amount} ${s.currency}`}
        defaultValues={() => ({ net_amount: "", currency, status: "RECEIVED" as SalaryStatus, notes: "" })}
        valuesFromRecord={(s) => ({
          net_amount: String(Number(s.net_amount)),
          currency: s.currency,
          status: s.status,
          notes: s.notes ?? "",
        })}
        onCreate={async (values: MoneyInFormValues) =>
          api.salaries.create({
            financial_period_id: period.id,
            net_amount: values.net_amount as string,
            currency: values.currency as string,
            status: values.status as SalaryStatus,
            notes: (values.notes as string | null) ?? null,
          })
        }
        onUpdate={async (id, values, expectedUpdatedAt) =>
          api.salaries.update(id, {
            net_amount: values.net_amount as string,
            currency: values.currency as string,
            status: values.status as SalaryStatus,
            notes: (values.notes as string | null) ?? null,
            expected_updated_at: expectedUpdatedAt,
          })
        }
        onDelete={(id) => api.salaries.remove(id)}
        columns={[
          {
            header: "Status",
            render: (s) => (
              <span className={s.status === "RECEIVED" ? "text-ontrack" : "text-planned"}>
                {humanizeEnum(s.status)}
              </span>
            ),
          },
          {
            header: "Net amount",
            className: "text-right",
            render: (s) => <AmountDisplay value={s.net_amount} currency={s.currency} />,
          },
          {
            header: "Notes",
            className: "max-w-xs truncate text-sm text-ink-soft",
            render: (s) => s.notes || "—",
          },
        ]}
      />
    </div>
  );
}
