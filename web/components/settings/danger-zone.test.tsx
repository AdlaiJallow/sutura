import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DangerZone } from "./danger-zone";
import { ApiError } from "@/lib/api";

afterEach(cleanup);

describe("<DangerZone /> — destructive-action confirmation flow", () => {
  it("does not delete anything until the confirmation dialog is opened and a password is entered", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<DangerZone onDelete={onDelete} />);

    // Just visiting the section calls nothing.
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByText("Danger zone")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete my account" }));
    expect(await screen.findByRole("heading", { name: "Delete your account?" })).toBeInTheDocument();

    // Submitting with no password entered is blocked client-side.
    await user.click(screen.getByRole("button", { name: "Permanently delete my account" }));
    expect(await screen.findByText("Enter your password to confirm.")).toBeInTheDocument();
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("calls onDelete with the entered password once confirmed", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn().mockResolvedValue(undefined);
    render(<DangerZone onDelete={onDelete} />);

    await user.click(screen.getByRole("button", { name: "Delete my account" }));
    await user.type(await screen.findByLabelText("Password"), "MyRealPassw0rd!");
    await user.click(screen.getByRole("button", { name: "Permanently delete my account" }));

    await vi.waitFor(() => expect(onDelete).toHaveBeenCalledWith("MyRealPassw0rd!"));
  });

  it("shows a wrong-password rejection inline in the dialog without pretending it succeeded", async () => {
    const user = userEvent.setup();
    const onDelete = vi
      .fn()
      .mockRejectedValue(new ApiError(401, { error: { code: "UNAUTHORIZED", message: "Password is incorrect." } }));
    render(<DangerZone onDelete={onDelete} />);

    await user.click(screen.getByRole("button", { name: "Delete my account" }));
    await user.type(await screen.findByLabelText("Password"), "WrongOne!");
    await user.click(screen.getByRole("button", { name: "Permanently delete my account" }));

    expect(await screen.findByText("Password is incorrect.")).toBeInTheDocument();
    // The dialog is still open, still asking for a password — nothing was silently applied.
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });
});
