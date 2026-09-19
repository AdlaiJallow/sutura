"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Logo } from "@/components/brand/logo";
import { useAuth } from "@/lib/auth-context";

/**
 * Client-side auth gate for every route under `(app)`. A Next.js middleware can't
 * do this — it can't read the in-memory access token or await the silent-refresh
 * call the way `AuthProvider` does — so this is deliberately a client component
 * (D-026 / Phase 5 part 1 handback).
 *
 * While the silent refresh is in flight ("checking"), no protected content or
 * shell renders — just a branded loading state, so there is never a flash of a
 * previous session's dashboard before a redirect. On failure, redirect to /login.
 */
export default function AppGroupLayout({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status !== "authenticated") {
    return (
      <div className="flex min-h-full flex-1 flex-col items-center justify-center gap-4 px-4">
        <Logo size="lg" />
        <div className="h-1 w-40 overflow-hidden rounded-full bg-secondary">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-rust-500" />
        </div>
        <p className="text-sm text-ink-soft">
          {status === "checking" ? "Checking your session…" : "Signing you out…"}
        </p>
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
