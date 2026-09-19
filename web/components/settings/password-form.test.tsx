import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PasswordForm } from "./password-form";
import { ApiError } from "@/lib/api";

afterEach(cleanup);

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  { current = "OldPassw0rd!", next = "NewPassw0rd!", confirm = "NewPassw0rd!" } = {},
) {
  await user.type(screen.getByLabelText("Current password"), current);
  await user.type(screen.getByLabelText("New password"), next);
  await user.type(screen.getByLabelText("Confirm new password"), confirm);
  await user.click(screen.getByRole("button", { name: "Change password" }));
}

describe("<PasswordForm /> — validation and submission", () => {
  it("requires a current password before submitting", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PasswordForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("New password"), "NewPassw0rd!");
    await user.type(screen.getByLabelText("Confirm new password"), "NewPassw0rd!");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText(/Enter your current password/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a new password under 8 characters in plain language", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { next: "short", confirm: "short" });

    expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("catches a confirm-password mismatch before submitting", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { confirm: "SomethingElse1!" });

    expect(await screen.findByText(/doesn't match/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits current/new password and shows a success confirmation, clearing the fields", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<PasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user);

    await vi.waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        current_password: "OldPassw0rd!",
        new_password: "NewPassw0rd!",
      }),
    );
    expect(await screen.findByText("Password updated.")).toBeInTheDocument();
    expect(screen.getByLabelText("Current password")).toHaveValue("");
  });

  it("pins a wrong-current-password 401 directly on that field, not a generic banner", async () => {
    const user = userEvent.setup();
    const onSubmit = vi
      .fn()
      .mockRejectedValue(new ApiError(401, { error: { code: "UNAUTHORIZED", message: "Current password is incorrect." } }));
    render(<PasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "WrongPassword1!" });

    const error = await screen.findByText("Current password is incorrect.");
    expect(error).toBeInTheDocument();
    // It's attached to the current-password field, not a page-level alert banner.
    expect(screen.getByLabelText("Current password")).toBeInTheDocument();
  });
});
