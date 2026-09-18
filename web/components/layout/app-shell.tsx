import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/brand/logo";
import { PeriodProvider } from "./period-context";
import { PeriodSelector } from "./period-selector";
import { WorkflowNav } from "./workflow-nav";
import { mockUser } from "@/lib/mock-data";

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
  return (
    <PeriodProvider>
      <div className="flex min-h-full flex-col">
        <header className="border-b border-line bg-paper-raised">
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
                title={mockUser.full_name}
                className="figure flex size-8 shrink-0 items-center justify-center rounded-full bg-rust-100 text-xs font-semibold text-rust-700 transition-colors duration-250 ease-ledger hover:bg-rust-300"
              >
                {initials(mockUser.full_name)}
              </Link>
            </div>
          </div>
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <WorkflowNav />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>
      </div>
    </PeriodProvider>
  );
}
