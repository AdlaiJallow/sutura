"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

const CURRENCY_RE = /^[A-Za-z]{3}$/;

export interface ProfileFormValues {
  full_name: string;
  default_currency: string;
}

export interface ProfileFormProps {
  profile: UserProfile;
  onSave: (values: ProfileFormValues) => Promise<UserProfile>;
}

/**
 * "Who you are" — the only two things a person can change about their own
 * identity in Sutura (name, default currency). Email is shown read-only:
 * there's no `PATCH /users/me` field for it, so offering an editable input
 * here would be a UI promise the backend can't keep.
 */
export function ProfileForm({ profile, onSave }: ProfileFormProps) {
  const [fullName, setFullName] = useState(profile.full_name ?? "");
  const [currency, setCurrency] = useState(profile.default_currency);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBanner(null);
    setSaved(false);

    const nextErrors: Record<string, string> = {};
    if (!fullName.trim()) {
      nextErrors.full_name = "Enter your name so we know whose account this is.";
    }
    if (!CURRENCY_RE.test(currency.trim())) {
      nextErrors.default_currency = "Currency must be a 3-letter code, e.g. GMD.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      const updated = await onSave({
        full_name: fullName.trim(),
        default_currency: currency.trim().toUpperCase(),
      });
      setFullName(updated.full_name ?? "");
      setCurrency(updated.default_currency);
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError) {
        const mapped: Record<string, string> = {};
        for (const fe of err.fieldErrors ?? []) {
          mapped[fe.field] = fe.message;
        }
        setErrors(mapped);
        if (Object.keys(mapped).length === 0) setBanner(err.message);
      } else {
        setBanner("Couldn't save your profile. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="settings-email">Email</Label>
        <div className="flex flex-wrap items-center gap-2">
          <Input id="settings-email" value={profile.email} disabled className="max-w-sm" />
          <span
            className={
              "shrink-0 text-xs font-medium " +
              (profile.is_email_verified ? "text-ontrack" : "text-ink-faint")
            }
          >
            {profile.is_email_verified ? "Verified" : "Not verified yet"}
          </span>
        </div>
        <p className="text-xs text-ink-faint">Your email can&apos;t be changed here.</p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="settings-full-name">Full name</Label>
        <Input
          id="settings-full-name"
          value={fullName}
          placeholder="e.g. Fatou Ceesay"
          className="max-w-sm"
          onChange={(e) => {
            setFullName(e.target.value);
            setSaved(false);
          }}
        />
        {errors.full_name && <p className="text-xs text-overspent">{errors.full_name}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="settings-currency">Default currency</Label>
        <Input
          id="settings-currency"
          value={currency}
          maxLength={3}
          className="w-24 uppercase"
          onChange={(e) => {
            setCurrency(e.target.value.toUpperCase());
            setSaved(false);
          }}
        />
        <p className="text-xs text-ink-faint">
          Used as the fallback currency for new records — a 3-letter code, e.g. GMD, USD.
        </p>
        {errors.default_currency && <p className="text-xs text-overspent">{errors.default_currency}</p>}
      </div>

      <div className="flex items-center gap-3 pt-1">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Save profile"}
        </Button>
        {saved && <span className="text-sm text-ontrack">Saved.</span>}
      </div>
    </form>
  );
}
