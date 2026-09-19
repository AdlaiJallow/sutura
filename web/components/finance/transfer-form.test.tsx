import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Dialog } from "@/components/ui/dialog";
import { TransferForm, type TransferFormProps } from "./transfer-form";
import { ApiError } from "@/lib/api";
import type { BankAccountSummary } from "@/lib/types";

afterEach(cleanup);

// `TransferForm` renders `DialogHeader`/`DialogTitle`/`DialogFooter` (it's always mounted
// inside a real `<Dialog>` in production — see app/(app)/transactions/page.tsx), and Radix's
// `DialogTitle` needs that context to exist even outside `DialogContent`, so every render here
// wraps it the same way.
function renderTransferForm(props: TransferFormProps) {
  return render(
    <Dialog open>
      <TransferForm {...props} />
    </Dialog>,
  );
}

const checking: BankAccountSummary = {
  id: "acc-checking",
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

const savingsVault: BankAccountSummary = {
  id: "acc-savings",
  account_name: "Savings Vault",
  institution_name: "Trust Bank",
  account_type: "SAVINGS",
  account_identifier_last4: "3322",
  currency: "GMD",
  opening_balance: "0.0000",
  current_balance: "500.0000",
  is_active: true,
  notes: null,
  updated_at: "2026-09-19T00:00:00Z",
};

const usdWallet: BankAccountSummary = {
  id: "acc-usd",
  account_name: "USD Wallet",
  institution_name: null,
  account_type: "OTHER",
  account_identifier_last4: null,
  currency: "USD",
  opening_balance: "0.0000",
  current_balance: "0.0000",
  is_active: true,
  notes: null,
  updated_at: "2026-09-19T00:00:00Z",
};

describe("<TransferForm /> — two distinct account pickers, no type selector", () => {
  it("renders From/To pickers and never a transaction-type selector", () => {
    renderTransferForm({ accounts: [checking, savingsVault], onSubmit: vi.fn() });

    expect(screen.getByText("From")).toBeInTheDocument();
    expect(screen.getByText("To")).toBeInTheDocument();
    expect(screen.queryByText(/type/i)).not.toBeInTheDocument();
  });

  it("blocks submitting with no accounts chosen and never calls onSubmit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderTransferForm({ accounts: [checking, savingsVault], onSubmit });

    await user.click(screen.getByRole("button", { name: "Transfer money" }));

    expect(await screen.findByText("Choose the account to move money from.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a valid transfer with the source account's currency, never free-typed", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderTransferForm({ accounts: [checking, savingsVault], onSubmit });

    await user.click(screen.getByLabelText("From"));
    await user.click(await screen.findByRole("option", { name: /Main Checking/ }));
    await user.click(screen.getByLabelText("To"));
    await user.click(await screen.findByRole("option", { name: /Savings Vault/ }));
    await user.type(screen.getByLabelText(/Amount/), "500");

    await user.click(screen.getByRole("button", { name: "Transfer money" }));

    await vi.waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        source_bank_account_id: "acc-checking",
        destination_bank_account_id: "acc-savings",
        amount: "500",
        currency: "GMD",
      }),
    );
  });

  it("catches a same-currency mismatch before submitting, in plain language", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderTransferForm({ accounts: [checking, usdWallet], onSubmit });

    await user.click(screen.getByLabelText("From"));
    await user.click(await screen.findByRole("option", { name: /Main Checking/ }));
    await user.click(screen.getByLabelText("To"));
    await user.click(await screen.findByRole("option", { name: /USD Wallet/ }));
    await user.type(screen.getByLabelText(/Amount/), "100");

    await user.click(screen.getByRole("button", { name: "Transfer money" }));

    expect(await screen.findByText(/different currencies/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("surfaces a rejected transfer (e.g. an inactive account) as a plain banner, not a crash", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockRejectedValue(new ApiError(422, { error: { code: "VALIDATION_ERROR", message: "Cannot transfer from an inactive bank account." } }));
    renderTransferForm({ accounts: [checking, savingsVault], onSubmit });

    await user.click(screen.getByLabelText("From"));
    await user.click(await screen.findByRole("option", { name: /Main Checking/ }));
    await user.click(screen.getByLabelText("To"));
    await user.click(await screen.findByRole("option", { name: /Savings Vault/ }));
    await user.type(screen.getByLabelText(/Amount/), "100");
    await user.click(screen.getByRole("button", { name: "Transfer money" }));

    expect(await screen.findByText("Cannot transfer from an inactive bank account.")).toBeInTheDocument();
  });
});
