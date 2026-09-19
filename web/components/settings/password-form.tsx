"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";

export interface PasswordFormValues {
  current_password: string;
  new_password: string;
}

export interface PasswordFormProps {
  onSubmit: (values: PasswordFormValues) => Promise<void>;
}

/**
 * Change-password: three fields (current, new, confirm), but only two ever
 * leave this component — `confirm` is a client-side typo-catcher, never sent.
 * A wrong `current_password` comes back from the backend as a 401 with no
 * `field_errors` (confirmed live against the running backend), so this is
 * the one place in the app that manually pins a fieldless API error onto a
 * specific input instead of falling back to a generic banner — the person
 * types their current password wrong, they should see the problem right
 * there, not have to guess which of three fields it was about.
 */
export function PasswordForm({ onSubmit }: PasswordFormProps) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBanner(null);
    setSuccess(false);

    const nextErrors: Record<string, string> = {};
    if (!currentPassword) {
      nextErrors.current_password = "Enter your current password.";
    }
    if (newPassword.length < 8) {
      nextErrors.new_password = "Use at least 8 characters for your new password.";
    }
    if (newPassword && confirmPassword !== newPassword) {
      nextErrors.confirm_password = "This doesn't match your new password.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await onSubmit({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setErrors({ current_password: err.message });
      } else if (err instanceof ApiError) {
        const mapped: Record<string, string> = {};
        for (const fe of err.fieldErrors ?? []) {
          mapped[fe.field] = fe.message;
        }
        setErrors(mapped);
        if (Object.keys(mapped).length === 0) setBanner(err.message);
      } else {
        setBanner("Couldn't change your password. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-sm space-y-4">
      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="settings-current-password">Current password</Label>
        <Input
          id="settings-current-password"
          type="password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(e) => {
            setCurrentPassword(e.target.value);
            setSuccess(false);
          }}
        />
        {errors.current_password && <p className="text-xs text-overspent">{errors.current_password}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="settings-new-password">New password</Label>
        <Input
          id="settings-new-password"
          type="password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(e) => {
            setNewPassword(e.target.value);
            setSuccess(false);
          }}
        />
        {errors.new_password ? (
          <p className="text-xs text-overspent">{errors.new_password}</p>
        ) : (
          <p className="text-xs text-ink-faint">At least 8 characters.</p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="settings-confirm-password">Confirm new password</Label>
        <Input
          id="settings-confirm-password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            setSuccess(false);
          }}
        />
        {errors.confirm_password && <p className="text-xs text-overspent">{errors.confirm_password}</p>}
      </div>

      <div className="flex items-center gap-3 pt-1">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Changing…" : "Change password"}
        </Button>
        {success && <span className="text-sm text-ontrack">Password updated.</span>}
      </div>
    </form>
  );
}
