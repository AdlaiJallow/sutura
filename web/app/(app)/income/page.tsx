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
import { humanizeEnum, monthLabel } from "@/lib/text";
import { useMoneyInList } from "@/lib/use-money-in-list";
import type { IncomeRecord, IncomeType } from "@/lib/types";

const INCOME_TYPE_OPTIONS: { value: IncomeType; label: string }[] = [
  { value: "IN_COUNTRY_PAYMENT", label: "In-country payment" },
  { value: "PER_DIEM", label: "Per diem" },
  { value: "FREELANCE", label: "Freelance" },
  { value: "BUSINESS", label: "Business" },
  { value: "INVESTMENT", label: "Investment" },
  { value: "OTHER", label: "Other" },
];

const FIELDS: MoneyInField[] = [
  {
    name: "income_type",
    label: "Type",
    type: "select",
    required: true,
    options: INCOME_TYPE_OPTIONS,
    helpText: "Salary and allowances have their own pages — this is for everything else.",
  },
  { name: "description", label: "Description", type: "text", required: true, placeholder: "e.g. Logo design for a client" },
  { name: "amount", label: "Amount", type: "amount", required: true, placeholder: "e.g. 4200" },
  { name: "currency", label: "Currency", type: "currency", required: true },
  { name: "date_received", label: "Date received", type: "date", required: true },
  { name: "source", label: "Source", type: "text", placeholder: "Optional — who paid you" },
  { name: "is_recurring", label: "This repeats every period", type: "checkbox" },
  { name: "notes", label: "Notes", type: "textarea", placeholder: "Optional" },
];

/**
 * Other income — anything that isn't salary or an allowance (D-007 deliberately
 * excludes those from `income_type`). Unlimited entries per period (spec §8).
 */
export default function IncomePage() {
  const { period } = usePeriod();
  const currency = period.base_currency;

  const fetchList = useCallback(() => api.income.list({ financial_period_id: period.id }), [period.id]);
  const { records, error, reload } = useMoneyInList(fetchList);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Other Income</h1>
        <p className="mt-1 max-w-md text-sm text-ink-soft">
          Anything else that came in during {monthLabel(period.year, period.month)} — freelance work,
          gifts, refunds — kept separate from salary and allowances.
        </p>
      </div>

      <MoneyInManager<IncomeRecord>
        period={period}
        fields={FIELDS}
        addLabel="Add income"
        singularLabel="income entry"
        emptyTitle="No other income yet"
        emptyMessage={`Add anything else you received in ${monthLabel(period.year, period.month)} outside of salary and allowances.`}
        records={records}
        error={error}
        onReload={reload}
        describeRecord={(i) => i.description}
        defaultValues={() => ({
          income_type: "",
          description: "",
          amount: "",
          currency,
          date_received: defaultDateReceived(),
          source: "",
          is_recurring: false,
          notes: "",
        })}
        valuesFromRecord={(i) => ({
          income_type: i.income_type,
          description: i.description,
          amount: String(Number(i.amount)),
          currency: i.currency,
          date_received: i.date_received,
          source: i.source ?? "",
          is_recurring: i.is_recurring,
          notes: i.notes ?? "",
        })}
        onCreate={async (values: MoneyInFormValues) =>
          api.income.create({
            financial_period_id: period.id,
            income_type: values.income_type as IncomeType,
            description: values.description as string,
            amount: values.amount as string,
            currency: values.currency as string,
            date_received: values.date_received as string,
            source: (values.source as string | null) ?? null,
            is_recurring: Boolean(values.is_recurring),
            notes: (values.notes as string | null) ?? null,
          })
        }
        onUpdate={async (id, values, expectedUpdatedAt) =>
          api.income.update(id, {
            income_type: values.income_type as IncomeType,
            description: values.description as string,
            amount: values.amount as string,
            currency: values.currency as string,
            date_received: values.date_received as string,
            source: (values.source as string | null) ?? null,
            is_recurring: Boolean(values.is_recurring),
            notes: (values.notes as string | null) ?? null,
            expected_updated_at: expectedUpdatedAt,
          })
        }
        onDelete={(id) => api.income.remove(id)}
        columns={[
          {
            header: "Type",
            className: "text-xs text-ink-faint",
            render: (i) => humanizeEnum(i.income_type),
          },
          { header: "Description", render: (i) => <span className="text-ink">{i.description}</span> },
          {
            header: "Amount",
            className: "text-right",
            render: (i) => <AmountDisplay value={i.amount} currency={i.currency} />,
          },
          {
            header: "Received",
            className: "figure text-xs text-ink-faint",
            render: (i) => formatLedgerDate(i.date_received),
          },
          {
            header: "Source",
            className: "text-xs text-ink-faint",
            render: (i) => i.source || "—",
          },
        ]}
      />
    </div>
  );
}
