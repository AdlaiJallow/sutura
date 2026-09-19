"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";

export interface DangerZoneProps {
  onDelete: (password: string) => Promise<void>;
}

/**
 * The one destructive, hard-to-undo action a person can take about their own
 * account. Visually set apart from Profile/Password using the same
 * overspent-red language the rest of the app already uses for "this is a
 * problem" states (`ErrorState`, an overspent category, a closed-period
 * conflict) — extended here to mean "this is dangerous," not invented fresh.
 *
 * The backend requires the current password in the request body to confirm
 * identity (confirmed live — `DELETE /users/me` 422s without one), so the
 * confirmation dialog asks for it directly rather than a bare "yes, delete"
 * button that would just fail server-side.
 */
export function DangerZone({ onDelete }: DangerZoneProps) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      setPassword("");
      setError(null);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!password) {
      setError("Enter your password to confirm.");
      return;
    }
    setSubmitting(true);
    try {
      await onDelete(password);
      // No need to reset local state on success — the page navigates away.
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't delete your account. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <section
      aria-labelledby="danger-zone-heading"
      className="rounded-md border border-overspent-bg bg-overspent-bg/30 p-6"
    >
      <h2 id="danger-zone-heading" className="font-display text-xl text-overspent">
        Danger zone
      </h2>
      <p className="mt-2 max-w-md text-sm text-ink-soft">
        Deleting your account deactivates it immediately: you&apos;ll be signed out and won&apos;t
        be able to sign back in. Your financial records aren&apos;t erased, but you lose access to
        them unless the account is restored on your behalf. This can&apos;t be undone from here.
      </p>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogTrigger asChild>
          <Button variant="destructive" className="mt-4">
            Delete my account
          </Button>
        </DialogTrigger>
        <DialogContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <DialogHeader>
              <DialogTitle>Delete your account?</DialogTitle>
              <DialogDescription>
                Confirm with your password. This deactivates your account right away — you&apos;ll
                be signed out and won&apos;t be able to sign back in.
              </DialogDescription>
            </DialogHeader>

            {error && (
              <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
                {error}
              </p>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="danger-zone-password">Password</Label>
              <Input
                id="danger-zone-password"
                type="password"
                autoComplete="current-password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <DialogFooter>
              <Button type="submit" variant="destructive" disabled={submitting}>
                {submitting ? "Deleting…" : "Permanently delete my account"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </section>
  );
}
