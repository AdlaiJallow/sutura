import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { buildExpenseFields } from "./expense-fields";
import { MoneyInManager } from "./money-in-manager";
import type { Expense } from "@/lib/types";
import type { FinancialPeriod, DistributionCategorySummary, BankAccountSummary } from "@/lib/types";

afterEach(cleanup);

const noCategories: DistributionCategorySummary[] = [];
const noBankAccounts: BankAccountSummary[] = [];

const categories: DistributionCategorySummary[] = [
  {
    id: "cat-needs",
    name: "Needs",
    percentage: "50.00",
    allocation: "10000.0000",
    used: "0.0000",
    remaining: "10000.0000",
    is_overspent: false,
    contributes_to_automatic_savings: false,
    is_unallocated_bucket: false,
  },
  {
    id: "cat-wants",
    name: "Wants",
    percentage: "30.00",
    allocation: "6000.0000",
    used: "0.0000",
    remaining: "6000.0000",
    is_overspent: false,
    contributes_to_automatic_savings: false,
    is_unallocated_bucket: false,
  },
];

describe("buildExpenseFields — no distribution rule selected yet", () => {
  it("omits the budget category field entirely rather than showing it optional (D-006)", () => {
    const fields = buildExpenseFields(noCategories, noBankAccounts);
    expect(fields.find((f) => f.name === "distribution_category_id")).toBeUndefined();
  });
});

describe("buildExpenseFields — a rule is selected for this period", () => {
  it("adds a required budget category field populated from the period's real categories, not free text", () => {
    const fields = buildExpenseFields(categories, noBankAccounts);
    const field = fields.find((f) => f.name === "distribution_category_id");
    expect(field).toBeDefined();
    expect(field?.required).toBe(true);
    expect(field?.type).toBe("select");
    expect(field?.options?.map((o) => o.value)).toEqual(["cat-needs", "cat-wants"]);
  });

  it("omits the optional 'Paid from' field when there are no bank accounts to offer", () => {
    const fields = buildExpenseFields(categories, noBankAccounts);
    expect(fields.find((f) => f.name === "bank_account_id")).toBeUndefined();
  });
});

const openPeriod: FinancialPeriod = {
  id: "period-1",
  year: 2026,
  month: 9,
  start_date: "2026-09-01",
  end_date: "2026-09-30",
  status: "OPEN",
  distribution_rule_id: "rule-1",
  base_currency: "GMD",
  closed_at: null,
  closed_by: null,
  reopened_count: 0,
  last_reopened_at: null,
};

/** Exercises the fields this exact function produces through the real
 * `MoneyInManager` form — not just the field-list shape — so the "category is
 * required once a rule exists" rule is proven in the rendered form, not just
 * asserted about the config object. */
describe("<MoneyInManager /> with expense fields — category select is required once a rule exists", () => {
  it("blocks submitting an expense with no budget category chosen", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();
    const fields = buildExpenseFields(categories, noBankAccounts);

    render(
      <MoneyInManager<Expense>
        period={openPeriod}
        fields={fields}
        addLabel="Add expense"
        singularLabel="expense"
        emptyTitle="No expenses yet"
        emptyMessage="Add one."
        records={[]}
        error={null}
        onReload={vi.fn()}
        describeRecord={(e) => e.name}
        defaultValues={() => ({
          name: "",
          expense_category: "",
          distribution_category_id: "",
          amount: "",
          currency: "GMD",
          expense_date: "2026-09-10",
          payment_method: "",
          notes: "",
        })}
        valuesFromRecord={() => ({})}
        onCreate={onCreate}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
        columns={[{ header: "Name", render: (e) => e.name }]}
      />,
    );

    await user.click(screen.getAllByRole("button", { name: "Add expense" })[0]);
    expect(screen.getByLabelText("Budget category")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Name"), "Rent");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Budget category is required.")).toBeInTheDocument();
    expect(onCreate).not.toHaveBeenCalled();
  });
});
