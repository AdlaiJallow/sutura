"use client";

import { useCallback } from "react";
import { AmountDisplay } from "@/components/finance/amount-display";
import {
  defaultDateReceived,
  MoneyInManager,
  type MoneyInField,
  type MoneyInFormValues,
} from "@/components/finance/money-in-manager";
import { usePeriod } from "@/components/layout/period-context";
import { api } from "@/lib/api";
import { formatLedgerDate } from "@/lib/money";
import { monthLabel } from "@/lib/text";
import { useMoneyInList } from "@/lib/use-money-in-list";
import type { Allowance } from "@/lib/types";

const FIELDS: MoneyInField[] = [
  { name: "name", label: "Name", type: "text", required: true, placeholder: "e.g. Transport allowance" },
  { name: "amount", label: "Amount", type: "amount", required: true, placeholder: "e.g. 1500" },
  { name: "currency", label: "Currency", type: "currency", required: true },
  { name: "date_received", label: "Date received", type: "date", required: true },
  { name: "is_recurring", label: "This repeats every period", type: "checkbox" },
  { name: "notes", label: "Notes", type: "textarea", placeholder: "Optional" },
];

/**
 * Allowances tracked separately from salary (spec §7) — unlimited entries per
 * period, each with its own date and optional recurring flag.
 */
export default function AllowancesPage() {
  const { period } = usePeriod();
  const currency = period.base_currency;

  const fetchList = useCallback(() => api.allowances.list({ financial_period_id: period.id }), [period.id]);
  const { records, error, reload } = useMoneyInList(fetchList);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Allowances</h1>
        <p className="mt-1 max-w-md text-sm text-ink-soft">
          Allowances for {monthLabel(period.year, period.month)} — recurring or one-off, tracked
          separately from your salary.
        </p>
      </div>

      <MoneyInManager<Allowance>
        period={period}
        fields={FIELDS}
        addLabel="Add allowance"
        singularLabel="allowance"
        emptyTitle="No allowances yet"
        emptyMessage={`Add an allowance for ${monthLabel(period.year, period.month)} — transport, housing, or anything else paid alongside salary.`}
        records={records}
        error={error}
        onReload={reload}
        describeRecord={(a) => a.name}
        defaultValues={() => ({
          name: "",
          amount: "",
          currency,
          date_received: defaultDateReceived(),
          is_recurring: false,
          notes: "",
        })}
        valuesFromRecord={(a) => ({
          name: a.name,
          amount: String(Number(a.amount)),
          currency: a.currency,
          date_received: a.date_received,
          is_recurring: a.is_recurring,
          notes: a.notes ?? "",
        })}
        onCreate={async (values: MoneyInFormValues) =>
          api.allowances.create({
            financial_period_id: period.id,
            name: values.name as string,
            amount: values.amount as string,
            currency: values.currency as string,
            is_recurring: Boolean(values.is_recurring),
            date_received: values.date_received as string,
            notes: (values.notes as string | null) ?? null,
          })
        }
        onUpdate={async (id, values, expectedUpdatedAt) =>
          api.allowances.update(id, {
            name: values.name as string,
            amount: values.amount as string,
            currency: values.currency as string,
            is_recurring: Boolean(values.is_recurring),
            date_received: values.date_received as string,
            notes: (values.notes as string | null) ?? null,
            expected_updated_at: expectedUpdatedAt,
          })
        }
        onDelete={(id) => api.allowances.remove(id)}
        columns={[
          { header: "Name", render: (a) => <span className="text-ink">{a.name}</span> },
          {
            header: "Amount",
            className: "text-right",
            render: (a) => <AmountDisplay value={a.amount} currency={a.currency} />,
          },
          {
            header: "Received",
            className: "figure text-xs text-ink-faint",
            render: (a) => formatLedgerDate(a.date_received),
          },
          {
            header: "Recurring",
            className: "text-xs text-ink-faint",
            render: (a) => (a.is_recurring ? "Yes" : "No"),
          },
        ]}
      />
    </div>
  );
}
