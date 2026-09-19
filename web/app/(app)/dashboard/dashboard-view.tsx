import Link from "next/link";
import { AmountDisplay } from "@/components/finance/amount-display";
import { StatusBadge } from "@/components/finance/status-badge";
import { ZeroIncomeEmptyState } from "@/components/finance/zero-income-empty-state";
import { isZero } from "@/lib/money";
import { monthLabel } from "@/lib/text";
import type { BankAccountSummary, FinancialPeriod, MonthlySummary, SavingsSummary } from "@/lib/types";

export interface DashboardViewProps {
  period: FinancialPeriod;
  summary: MonthlySummary;
  savings: SavingsSummary;
  accounts: BankAccountSummary[];
}

/**
 * NOTE on scope (Phase 5 part 1): `GET /financial-periods/{id}/summary` returns a
 * flat cache row (income + expense + savings totals only) — there is currently no
 * backend endpoint for per-category allocation/used/remaining or spending-by-category
 * breakdowns (see the `DistributionView` doc comment in lib/types.ts). Those sections
 * come back once that endpoint exists; this view only renders numbers the backend
 * actually returns today.
 */
export function DashboardView({ period, summary, savings, accounts }: DashboardViewProps) {
  const currency = period.base_currency;
  const hasIncome = !isZero(summary.total_monthly_income);
  const label = monthLabel(period.year, period.month);

  return (
    <div className="animate-fade-in space-y-12">
      {/* Hero: the one number a person opens this app to check. */}
      <section>
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold tracking-wideish text-rust-500 uppercase">
          <span>{label}</span>
          <StatusBadge status={period.status} />
          {period.reopened_count > 0 && <StatusBadge status="MODIFIED" />}
        </div>
        <h1 className="mt-2 font-display text-4xl text-ink md:text-5xl">Money Available</h1>
        <AmountDisplay
          value={summary.total_monthly_income}
          currency={currency}
          size="xl"
          weight="semibold"
          className="mt-1"
        />
        <p className="mt-2 max-w-md text-sm text-ink-soft">
          Your total income for {label} — salary, allowances, and everything else that came in.
        </p>
      </section>

      {!hasIncome ? (
        <ZeroIncomeEmptyState periodLabel={label} />
      ) : (
        <>
          {/* Income breakdown */}
          <section>
            <h2 className="font-display text-xl text-ink">Where it came from</h2>
            <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-4">
              <Stat
                label="Salary & Allowances"
                value={summary.total_salary_income}
                currency={currency}
              />
              <Stat label="Of Which, Allowances" value={summary.total_allowances} currency={currency} />
              <Stat label="Other Income" value={summary.total_other_income} currency={currency} />
              <Stat
                label="Total Monthly Income"
                value={summary.total_monthly_income}
                currency={currency}
                emphasize
              />
            </div>
          </section>

          {/* Spending & plan */}
          <section>
            <h2 className="font-display text-xl text-ink">Spending & Plan</h2>
            <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-3">
              <Stat label="Spent So Far" value={summary.total_expenses} currency={currency} />
              <Stat label="Planned Savings" value={summary.total_planned_savings} currency={currency} />
              <Stat
                label="Sent to Bank Accounts"
                value={summary.total_bank_deposits}
                currency={currency}
              />
            </div>
            <p className="mt-3 text-xs text-ink-faint">
              A category-by-category breakdown of planned vs. spent is coming once
              distribution rules are set up (see{" "}
              <Link href="/distribution" className="font-medium text-rust-500 hover:text-rust-700">
                Distribution
              </Link>
              ).
            </p>
          </section>

          {/* Savings — from the live `/savings/{period}` rollup, not the period-close
              snapshot, so it reflects the most recent expense/manual-savings edits. */}
          <section>
            <h2 className="font-display text-xl text-ink">Saved</h2>
            <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-4">
              <Stat
                label="Saved Automatically"
                value={savings.automatic_savings_computed}
                currency={currency}
                tone="positive"
              />
              <Stat
                label="Saved Manually"
                value={savings.manual_savings_total}
                currency={currency}
                tone="positive"
              />
              <Stat
                label="Total Saved"
                value={savings.final_savings_total}
                currency={currency}
                tone="positive"
                emphasize
              />
              <Stat label="Sent to Accounts" value={savings.distributed_total} currency={currency} />
            </div>
            {!isZero(savings.undistributed_total) &&
              (() => {
                const shortfall = savingsIsShortfall(savings.undistributed_total);
                return (
                  <div
                    className={
                      "mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border px-4 py-3 " +
                      (shortfall ? "border-overspent-bg bg-overspent-bg/40" : "border-saved-bg bg-saved-bg")
                    }
                  >
                    <p className="text-sm text-ink">
                      <span className="font-semibold">
                        <AmountDisplay
                          value={savings.undistributed_total}
                          currency={currency}
                          size="sm"
                          tone="auto"
                        />
                      </span>{" "}
                      {shortfall
                        ? "more has been sent to accounts than your current savings cover — check your recent allocations."
                        : "hasn't been sent to an account or savings goal yet."}
                    </p>
                    <Link
                      href="/savings"
                      className="text-sm font-semibold text-rust-500 transition-colors duration-250 ease-ledger hover:text-rust-700"
                    >
                      {shortfall ? "Review savings" : "Assign it"} &rarr;
                    </Link>
                  </div>
                );
              })()}
          </section>
        </>
      )}

      {/* Accounts — shown regardless of this period's income, since balances persist. */}
      <section>
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="font-display text-xl text-ink">Your Accounts</h2>
          <Link
            href="/bank-accounts"
            className="text-sm font-medium text-rust-500 transition-colors duration-250 ease-ledger hover:text-rust-700"
          >
            View all &rarr;
          </Link>
        </div>
        {accounts.length === 0 ? (
          <p className="mt-4 text-sm text-ink-soft">No accounts added yet.</p>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {accounts.map((account) => (
              <div key={account.id} className="rounded-md border border-line bg-card p-4">
                <p className="font-display text-base text-ink">{account.account_name}</p>
                <p className="text-xs text-ink-faint">
                  {account.institution_name ?? "No institution on file"}
                  {account.account_identifier_last4
                    ? ` · •••• ${account.account_identifier_last4}`
                    : ""}
                </p>
                <AmountDisplay value={account.current_balance} currency={account.currency} size="lg" className="mt-2" />
                <p className="mt-1 text-xs text-ink-faint">Current balance</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function savingsIsShortfall(value: string): boolean {
  return Number(value) < 0;
}

function Stat({
  label,
  value,
  currency,
  tone = "neutral",
  emphasize = false,
}: {
  label: string;
  value: string;
  currency: string;
  tone?: "neutral" | "positive";
  emphasize?: boolean;
}) {
  return (
    <div className={emphasize ? "bg-accent p-4" : "bg-card p-4"}>
      <p className="text-[0.6875rem] font-medium tracking-wideish text-ink-faint uppercase">{label}</p>
      <AmountDisplay
        value={value}
        currency={currency}
        size={emphasize ? "lg" : "md"}
        tone={tone}
        weight={emphasize ? "semibold" : "medium"}
        className="mt-1"
      />
    </div>
  );
}
