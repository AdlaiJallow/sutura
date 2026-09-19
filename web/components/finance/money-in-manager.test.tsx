import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MoneyInManager, type MoneyInField, type MoneyInRecordBase } from "./money-in-manager";
import type { FinancialPeriod } from "@/lib/types";

// This suite renders the same "Edit"/"Delete"/"Add allowance" labels in every
// test — without an explicit cleanup, testing-library's DOM would accumulate
// across `it` blocks in this file (vitest.config.ts doesn't set `test.globals`,
// so testing-library's automatic afterEach cleanup never registers).
afterEach(cleanup);

// Exercises the manager with an allowance-shaped config (text + amount +
// currency + date + checkbox fields) since salary/allowances/income all share
// this exact component — one shared test suite instead of three near-identical
// ones (Phase 5 part 2 handback notes).
interface TestRecord extends MoneyInRecordBase {
  name: string;
  amount: string;
  currency: string;
  date_received: string;
  is_recurring: boolean;
}

const FIELDS: MoneyInField[] = [
  { name: "name", label: "Name", type: "text", required: true },
  { name: "amount", label: "Amount", type: "amount", required: true },
  { name: "currency", label: "Currency", type: "currency", required: true },
  { name: "date_received", label: "Date received", type: "date", required: true },
  { name: "is_recurring", label: "This repeats every period", type: "checkbox" },
];

const openPeriod: FinancialPeriod = {
  id: "period-1",
  year: 2026,
  month: 9,
  start_date: "2026-09-01",
  end_date: "2026-09-30",
  status: "OPEN",
  distribution_rule_id: null,
  base_currency: "GMD",
  closed_at: null,
  closed_by: null,
  reopened_count: 0,
  last_reopened_at: null,
};

const record: TestRecord = {
  id: "rec-1",
  updated_at: "2026-09-10T00:00:00Z",
  name: "Transport allowance",
  amount: "1500.0000",
  currency: "GMD",
  date_received: "2026-09-05",
  is_recurring: true,
};

function baseProps() {
  return {
    period: openPeriod,
    fields: FIELDS,
    addLabel: "Add allowance",
    singularLabel: "allowance",
    emptyTitle: "No allowances yet",
    emptyMessage: "Add one to get started.",
    describeRecord: (r: TestRecord) => r.name,
    defaultValues: () => ({ name: "", amount: "", currency: "GMD", date_received: "2026-09-10", is_recurring: false }),
    valuesFromRecord: (r: TestRecord) => ({
      name: r.name,
      amount: r.amount,
      currency: r.currency,
      date_received: r.date_received,
      is_recurring: r.is_recurring,
    }),
    onCreate: vi.fn(),
    onUpdate: vi.fn(),
    onDelete: vi.fn(),
    onReload: vi.fn(),
    columns: [
      { header: "Name", render: (r: TestRecord) => r.name },
      { header: "Amount", render: (r: TestRecord) => `${r.currency} ${r.amount}` },
    ],
  };
}

describe("<MoneyInManager /> — zero-income / empty state (spec §38)", () => {
  it("shows the empty state with an Add action instead of a blank table", () => {
    render(<MoneyInManager<TestRecord> {...baseProps()} records={[]} error={null} />);

    expect(screen.getByText("No allowances yet")).toBeInTheDocument();
    expect(screen.getByText("Add one to get started.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Add allowance" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("<MoneyInManager /> — populated list", () => {
  it("renders a row per record with Edit/Delete actions", () => {
    render(<MoneyInManager<TestRecord> {...baseProps()} records={[record]} error={null} />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Transport allowance")).toBeInTheDocument();
    expect(screen.getByText("GMD 1500.0000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("blocks submitting a record missing a required field with a plain-language error, and never calls onCreate", async () => {
    const user = userEvent.setup();
    const props = baseProps();
    render(<MoneyInManager<TestRecord> {...props} records={[record]} error={null} />);

    await user.click(screen.getByRole("button", { name: "Add allowance" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Name is required.")).toBeInTheDocument();
    expect(props.onCreate).not.toHaveBeenCalled();
  });

  it("hides Edit/Delete and the Add action, and explains why, when the period is closed", () => {
    const closedPeriod: FinancialPeriod = { ...openPeriod, status: "CLOSED" };
    render(<MoneyInManager<TestRecord> {...baseProps()} period={closedPeriod} records={[record]} error={null} />);

    expect(screen.getByText(/this period is closed/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add allowance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("hides the Add action once maxRecords is reached (D-008 — one salary per period)", () => {
    render(<MoneyInManager<TestRecord> {...baseProps()} maxRecords={1} records={[record]} error={null} />);
    expect(screen.queryByRole("button", { name: "Add allowance" })).not.toBeInTheDocument();
  });

  it("surfaces a backend error as a retryable error state instead of an empty table", () => {
    const props = baseProps();
    render(<MoneyInManager<TestRecord> {...props} records={null} error="Couldn't reach the Sutura server." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't reach the Sutura server.");
  });

  it("calls onUpdate with the record's own updated_at as the optimistic-lock token when editing", async () => {
    const user = userEvent.setup();
    const props = baseProps();
    props.onUpdate.mockResolvedValue({ ...record, name: "Transport allowance (updated)" });
    render(<MoneyInManager<TestRecord> {...props} records={[record]} error={null} />);

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const nameInput = await screen.findByLabelText("Name");
    await user.clear(nameInput);
    await user.type(nameInput, "Updated name");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(props.onUpdate).toHaveBeenCalledTimes(1));
    expect(props.onUpdate).toHaveBeenCalledWith(
      "rec-1",
      expect.objectContaining({ name: "Updated name" }),
      "2026-09-10T00:00:00Z",
    );
  });
});
