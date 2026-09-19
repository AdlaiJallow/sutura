"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DangerZone } from "@/components/settings/danger-zone";
import { PasswordForm, type PasswordFormValues } from "@/components/settings/password-form";
import { ProfileForm, type ProfileFormValues } from "@/components/settings/profile-form";
import { ErrorState } from "@/components/layout/error-state";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { UserProfile } from "@/lib/types";

/**
 * Profile, password, and account deletion — the three things spec §32 lists
 * for this route. Fetches its own fresh `GET /users/me` (rather than trusting
 * `useAuth().user`, which is best-effort and may be stale) so the form always
 * starts from what the backend actually has on file.
 */
export default function SettingsPage() {
  const router = useRouter();
  const { logout, refreshUser } = useAuth();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.users.me();
      setProfile(res);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Couldn't load your account details. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function handleSaveProfile(values: ProfileFormValues): Promise<UserProfile> {
    const updated = await api.users.update(values);
    setProfile(updated);
    await refreshUser();
    return updated;
  }

  async function handleChangePassword(values: PasswordFormValues): Promise<void> {
    await api.users.changePassword(values);
  }

  async function handleDeleteAccount(password: string): Promise<void> {
    await api.users.deleteMe({ password });
    await logout();
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="h-8 w-40 animate-pulse rounded-md bg-secondary" />
        <div className="h-40 animate-pulse rounded-md bg-secondary" />
      </div>
    );
  }

  if (error || !profile) {
    return <ErrorState message={error ?? undefined} onRetry={load} />;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-12 pb-16">
      <header>
        <h1 className="font-display text-3xl text-ink">Settings</h1>
        <p className="mt-1 max-w-md text-sm text-ink-soft">
          Your profile, password, and account.
        </p>
      </header>

      <section>
        <h2 className="font-display text-xl text-ink">Profile</h2>
        <div className="mt-4">
          <ProfileForm profile={profile} onSave={handleSaveProfile} />
        </div>
      </section>

      <section>
        <h2 className="font-display text-xl text-ink">Password</h2>
        <div className="mt-4">
          <PasswordForm onSubmit={handleChangePassword} />
        </div>
      </section>

      <DangerZone onDelete={handleDeleteAccount} />
    </div>
  );
}
