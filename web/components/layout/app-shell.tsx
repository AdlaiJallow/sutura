"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { LogOutIcon } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { PeriodProvider } from "./period-context";
import { PeriodSelector } from "./period-selector";
import { WorkflowNav } from "./workflow-nav";
import { useAuth } from "@/lib/auth-context";

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

/**
 * The shell every authenticated route renders inside: wordmark + period
 * switcher up top, a horizontal workflow nav strip below it (see
 * WorkflowNav for the navigation-design rationale), and the page body.
 * No sidebar — this is a data-dense but linear monthly workflow, and a top
 * strip keeps the full width available for tables/charts (Design identity:
 * "rethink navigation... consider tabs... top navigation").
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    await logout();
    router.push("/login");
  }

  const displayName = user?.full_name ?? user?.email ?? null;

  return (
    <PeriodProvider>
      <div className="flex min-h-full flex-col">
        <header className="border-b border-line bg-paper-raised print:hidden">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
            <Link href="/dashboard" className="flex items-baseline gap-2">
              <Logo size="lg" />
              <span className="hidden text-xs text-ink-faint sm:inline">
                every dalasi, accounted for
              </span>
            </Link>
            <div className="flex items-center gap-3">
              <PeriodSelector />
              <Link
                href="/settings"
                title={displayName ?? "Your account"}
                className="figure flex size-8 shrink-0 items-center justify-center rounded-full bg-rust-100 text-xs font-semibold text-rust-700 transition-colors duration-250 ease-ledger hover:bg-rust-300"
              >
                {displayName ? initials(displayName) : "…"}
              </Link>
              <button
                type="button"
                onClick={handleSignOut}
                disabled={signingOut}
                title="Sign out"
                aria-label="Sign out"
                className="flex size-8 shrink-0 items-center justify-center rounded-full text-ink-faint transition-colors duration-250 ease-ledger hover:bg-secondary hover:text-ink disabled:opacity-50"
              >
                <LogOutIcon className="size-4" aria-hidden />
              </button>
            </div>
          </div>
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <WorkflowNav />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 print:max-w-none print:p-0">
          {children}
        </main>
      </div>
    </PeriodProvider>
  );
}
