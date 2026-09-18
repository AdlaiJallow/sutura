"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
}

// Grouped in the order money actually moves through the app (CLAUDE.md:
// salary → allocation → spending → savings → banks) rather than an
// alphabetical or CRUD-table listing — this *is* the navigation design
// decision: a workflow strip, not a generic sidebar (Design identity §).
const NAV_GROUPS: NavItem[][] = [
  [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Periods", href: "/financial-periods" },
  ],
  [
    { label: "Salary", href: "/salary" },
    { label: "Allowances", href: "/allowances" },
    { label: "Income", href: "/income" },
  ],
  [
    { label: "Distribution", href: "/distribution" },
    { label: "Expenses", href: "/expenses" },
  ],
  [
    { label: "Savings", href: "/savings" },
    { label: "Bank Accounts", href: "/bank-accounts" },
    { label: "Transactions", href: "/transactions" },
  ],
  [
    { label: "Reports", href: "/reports" },
    { label: "Analytics", href: "/analytics" },
  ],
  [{ label: "Settings", href: "/settings" }],
];

export function WorkflowNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="ledger-scroll -mx-4 flex items-stretch gap-6 overflow-x-auto border-b border-line px-4 sm:mx-0 sm:px-0"
    >
      {NAV_GROUPS.map((group, i) => (
        <div key={i} className="flex shrink-0 items-stretch gap-1">
          {i > 0 && <span className="mr-5 self-center text-line" aria-hidden>|</span>}
          {group.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex items-center whitespace-nowrap px-2 py-3 text-[0.8125rem] font-medium tracking-tightish text-ink-faint transition-colors duration-250 ease-ledger hover:text-ink",
                  active && "text-ink",
                )}
              >
                {item.label}
                <span
                  className={cn(
                    "absolute inset-x-1 -bottom-px h-0.5 rounded-full bg-rust-500 transition-transform duration-250 ease-ledger",
                    active ? "scale-x-100" : "scale-x-0",
                  )}
                  aria-hidden
                />
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
