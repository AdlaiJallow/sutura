import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProfileForm } from "./profile-form";
import { ApiError } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

afterEach(cleanup);

const profile: UserProfile = {
  id: "user-1",
  email: "fatou.ceesay@example.com",
  full_name: "Fatou Ceesay",
  default_currency: "GMD",
  is_email_verified: true,
  mfa_enabled: false,
  is_active: true,
};

describe("<ProfileForm /> — validation and submission", () => {
  it("shows the email read-only and its verification state", () => {
    render(<ProfileForm profile={profile} onSave={vi.fn()} />);
    expect(screen.getByLabelText("Email")).toBeDisabled();
    expect(screen.getByDisplayValue("fatou.ceesay@example.com")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
  });

  it("blocks submitting a blank name and never calls onSave", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ProfileForm profile={profile} onSave={onSave} />);

    await user.clear(screen.getByLabelText("Full name"));
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(await screen.findByText(/Enter your name/i)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("blocks a currency that isn't a 3-letter code", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ProfileForm profile={profile} onSave={onSave} />);

    const currency = screen.getByLabelText("Default currency");
    await user.clear(currency);
    await user.type(currency, "US");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(await screen.findByText(/must be a 3-letter code/i)).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("submits trimmed, uppercased values and shows a saved confirmation", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue({ ...profile, full_name: "Fatou N. Ceesay", default_currency: "USD" });
    render(<ProfileForm profile={profile} onSave={onSave} />);

    const name = screen.getByLabelText("Full name");
    await user.clear(name);
    await user.type(name, "  Fatou N. Ceesay  ");
    const currency = screen.getByLabelText("Default currency");
    await user.clear(currency);
    await user.type(currency, "usd");

    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await vi.waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({ full_name: "Fatou N. Ceesay", default_currency: "USD" }),
    );
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  it("surfaces a rejected save as a plain banner, not a crash", async () => {
    const user = userEvent.setup();
    const onSave = vi
      .fn()
      .mockRejectedValue(new ApiError(422, { error: { code: "VALIDATION_ERROR", message: "default_currency must be a 3-letter ISO 4217 code." } }));
    render(<ProfileForm profile={profile} onSave={onSave} />);

    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(await screen.findByText("default_currency must be a 3-letter ISO 4217 code.")).toBeInTheDocument();
  });
});
