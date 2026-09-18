"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/layout/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

interface FormErrors {
  fullName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  form?: string;
}

function validateEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function validate(): FormErrors {
    const next: FormErrors = {};
    if (!fullName.trim()) next.fullName = "Tell us your name.";
    if (!email) next.email = "Enter your email address.";
    else if (!validateEmail(email)) next.email = "That doesn't look like a valid email address.";
    if (!password) next.password = "Choose a password.";
    else if (password.length < 8) next.password = "Use at least 8 characters.";
    if (confirmPassword !== password) next.confirmPassword = "Passwords don't match.";
    return next;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await api.auth.register({ email, password, full_name: fullName });
      setSubmitted(true);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Something went wrong creating your account. Please try again.";
      setErrors({ form: message });
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <AuthShell title="Check your email" subtitle="One more step before you're in.">
        <p className="text-sm text-ink-soft">
          We sent a verification link to <span className="font-semibold text-ink">{email}</span>.
          Follow it to activate your account, then sign in.
        </p>
        <Button className="mt-6 w-full" onClick={() => router.push("/login")}>
          Go to sign in
        </Button>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start planning your salary in a few minutes."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-rust-500 hover:text-rust-700">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="fullName">Full name</Label>
          <Input
            id="fullName"
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            aria-invalid={!!errors.fullName}
            placeholder="Fatou Ceesay"
          />
          {errors.fullName && <p className="text-xs text-overspent">{errors.fullName}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={!!errors.email}
            placeholder="you@example.com"
          />
          {errors.email && <p className="text-xs text-overspent">{errors.email}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={!!errors.password}
          />
          {errors.password && <p className="text-xs text-overspent">{errors.password}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirmPassword">Confirm password</Label>
          <Input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            aria-invalid={!!errors.confirmPassword}
          />
          {errors.confirmPassword && <p className="text-xs text-overspent">{errors.confirmPassword}</p>}
        </div>
        {errors.form && (
          <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
            {errors.form}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthShell>
  );
}
