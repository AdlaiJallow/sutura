import Link from "next/link";
import type { ReactNode } from "react";

const WORKFLOW_STEPS = ["Salary & income", "Distribution", "Spending", "Savings", "Bank accounts"];

/** Shared frame for /login and /register — a split editorial cover instead of
 * a generic centered card, so the very first screen someone sees already
 * commits to the design identity (Design identity: "screenshot test"). */
export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="grid min-h-full flex-1 lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-ink px-10 py-12 text-paper lg:flex">
        <Link href="/" className="font-display text-2xl font-semibold tracking-tightish">
          Sutura
        </Link>
        <div>
          <p className="font-display text-4xl leading-tight text-balance">
            Know where every dalasi goes.
          </p>
          <ol className="mt-10 space-y-3 text-sm text-paper/70">
            {WORKFLOW_STEPS.map((step, i) => (
              <li key={step} className="flex items-center gap-3">
                <span className="figure text-xs text-rust-300">{String(i + 1).padStart(2, "0")}</span>
                {step}
              </li>
            ))}
          </ol>
        </div>
        <p className="max-w-xs text-xs text-paper/50">
          Salary, allowances, and income flow into a plan you set — spending, saving, and every
          account stays visible in one ledger.
        </p>
      </div>
      <div className="flex flex-1 items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <Link href="/" className="font-display text-xl font-semibold text-ink lg:hidden">
            Sutura
          </Link>
          <h1 className="mt-6 font-display text-3xl text-ink lg:mt-0">{title}</h1>
          <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-6 text-sm text-ink-soft">{footer}</div>}
        </div>
      </div>
    </div>
  );
}
