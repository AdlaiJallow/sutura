// Builds the dynamic `MoneyInField[]` for the expense form (see
// app/(app)/expenses/page.tsx). Extracted as a pure function so its central
// rule — the "Budget category" field only exists, and is only required, once
// the period actually has distribution categories (D-006) — can be unit
// tested directly without rendering the whole page (expense-fields.test.ts).
import type { MoneyInField } from "./money-in-manager";
import { humanizeEnum } from "@/lib/text";
import type { BankAccountSummary, DistributionCategorySummary, ExpenseCategory, PaymentMethod } from "@/lib/types";

export const EXPENSE_CATEGORY_VALUES: ExpenseCategory[] = [
  "RENT",
  "FOOD",
  "TRANSPORTATION",
  "ELECTRICITY",
  "WATER",
  "INTERNET",
  "PHONE",
  "EDUCATION",
  "HEALTHCARE",
  "FAMILY_SUPPORT",
  "ENTERTAINMENT",
  "SHOPPING",
  "DEBT_REPAYMENT",
  "OTHER",
];
export const EXPENSE_CATEGORY_OPTIONS = EXPENSE_CATEGORY_VALUES.map((c) => ({ value: c, label: humanizeEnum(c) }));

export const PAYMENT_METHOD_VALUES: PaymentMethod[] = ["CASH", "BANK_TRANSFER", "CARD", "MOBILE_MONEY", "OTHER"];
export const PAYMENT_METHOD_OPTIONS = PAYMENT_METHOD_VALUES.map((m) => ({ value: m, label: humanizeEnum(m) }));

/**
 * `categories` is this period's real `DistributionView.categories` — never a
 * free-text field, and never populated until the backend actually has them
 * (spec §32/CLAUDE.md §27: the frontend renders what the API returns, it
 * doesn't invent a category list). When empty (no rule selected for this
 * period yet), the field is omitted entirely rather than shown-but-optional,
 * since a category id would have nothing valid to reference.
 */
export function buildExpenseFields(
  categories: DistributionCategorySummary[],
  bankAccounts: BankAccountSummary[],
): MoneyInField[] {
  const categoryRequired = categories.length > 0;

  const fields: MoneyInField[] = [
    { name: "name", label: "Name", type: "text", required: true, placeholder: "e.g. September groceries" },
    {
      name: "expense_category",
      label: "Category",
      type: "select",
      required: true,
      options: EXPENSE_CATEGORY_OPTIONS,
    },
  ];

  if (categoryRequired) {
    fields.push({
      name: "distribution_category_id",
      label: "Budget category",
      type: "select",
      required: true,
      options: categories.map((c) => ({ value: c.id, label: `${c.name} (${c.percentage}%)` })),
      helpText: "Which of this period's budget categories this counts against.",
    });
  }

  fields.push(
    { name: "amount", label: "Amount", type: "amount", required: true, placeholder: "e.g. 850" },
    { name: "currency", label: "Currency", type: "currency", required: true },
    { name: "expense_date", label: "Date", type: "date", required: true },
    {
      name: "payment_method",
      label: "Payment method",
      type: "select",
      options: PAYMENT_METHOD_OPTIONS,
      helpText: "Optional",
    },
  );

  if (bankAccounts.length > 0) {
    fields.push({
      name: "bank_account_id",
      label: "Paid from",
      type: "select",
      helpText: "Optional",
      options: bankAccounts.map((a) => ({
        value: a.id,
        label: a.account_identifier_last4 ? `${a.account_name} ••${a.account_identifier_last4}` : a.account_name,
      })),
    });
  }

  fields.push({ name: "notes", label: "Notes", type: "textarea", placeholder: "Optional" });
  return fields;
}
