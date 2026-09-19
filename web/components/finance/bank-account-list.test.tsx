import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BankAccountList } from "./bank-account-list";
import type { BankAccountSummary } from "@/lib/types";

afterEach(cleanup);

const active: BankAccountSummary = {
  id: "acc-1",
  account_name: "Main Checking",
  institution_name: "Trust Bank",
  account_type: "BANK",
  account_identifier_last4: "3456",
  currency: "GMD",
  opening_balance: "5000.0000",
  current_balance: "5300.0000",
  is_active: true,
  notes: null,
  updated_at: "2026-09-19T00:00:00Z",
};

const inactiveNoIdentifier: BankAccountSummary = {
  id: "acc-2",
  account_name: "Old Wallet",
  institution_name: null,
  account_type: "MOBILE_MONEY",
  account_identifier_last4: null,
  currency: "GMD",
  opening_balance: "0.0000",
  current_balance: "0.0000",
  is_active: false,
  notes: null,
  updated_at: "2026-09-19T00:00:00Z",
};

describe("<BankAccountList /> — masking and active/inactive states (spec §35/§38)", () => {
  it("shows only the last 4 digits of an identifier, never the full number", () => {
    render(<BankAccountList accounts={[active]} onEdit={vi.fn()} onToggleActive={vi.fn()} />);
    expect(screen.getByText("•••• 3456")).toBeInTheDocument();
  });

  it("distinguishes an active account with an Active badge and a Deactivate action", () => {
    render(<BankAccountList accounts={[active]} onEdit={vi.fn()} onToggleActive={vi.fn()} />);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deactivate" })).toBeInTheDocument();
  });

  it("distinguishes an inactive account with an Inactive badge, a Reactivate action, and no fabricated identifier", () => {
    render(<BankAccountList accounts={[inactiveNoIdentifier]} onEdit={vi.fn()} onToggleActive={vi.fn()} />);
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reactivate" })).toBeInTheDocument();
    expect(screen.getByText("No identifier on file")).toBeInTheDocument();
  });

  it("calls onEdit/onToggleActive with the clicked account", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    const onToggleActive = vi.fn();
    render(<BankAccountList accounts={[active]} onEdit={onEdit} onToggleActive={onToggleActive} />);

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(onEdit).toHaveBeenCalledWith(active);

    await user.click(screen.getByRole("button", { name: "Deactivate" }));
    expect(onToggleActive).toHaveBeenCalledWith(active);
  });
});
