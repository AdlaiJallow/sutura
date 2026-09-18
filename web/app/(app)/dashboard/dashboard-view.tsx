import Link from "next/link";
import { AmountDisplay } from "@/components/finance/amount-display";
import { StatusBadge } from "@/components/finance/status-badge";
import { CategoryProgressBar } from "@/components/finance/category-progress-bar";
import { SpendingByCategoryChart } from "@/components/finance/spending-by-category-chart";
import { ZeroIncomeEmptyState } from "@/components/finance/zero-income-empty-state";
import { isZero } from "@/lib/money";
import { monthLabel } from "@/lib/text";
import type { BankAccountSummary, DistributionView, FinancialPeriod, PeriodSummary } from "@/lib/types";

export interface DashboardViewProps {
  period: FinancialPeriod;
  summary: PeriodSummary;
  distribution: DistributionView;
  accounts: BankAccountSummary[];
}

export function DashboardView({ period, summary, distribution, accounts }: DashboardViewProps) {
  const currency = period.base_currency;
  const hasIncome = !isZero(summary.income.total_monthly_income);
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
          value={summary.income.total_monthly_income}
          currency={currency}
          size="xl"
          weight="semibold"
          className="mt-1"
        />
        <p className="mt-2 max-w-md text-sm text-ink-soft">
          Your total income for {label} — net salary, allowances, and everything else that came in.
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
              <Stat label="Net Salary" value={summary.income.net_salary} currency={currency} />
              <Stat label="Allowances" value={summary.income.total_allowances} currency={currency} />
              <Stat label="Other Income" value={summary.income.other_income} currency={currency} />
              <Stat
                label="Total Monthly Income"
                value={summary.income.total_monthly_income}
                currency={currency}
                emphasize
              />
            </div>
          </section>

          {/* Distribution / allocation */}
          <section>
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="font-display text-xl text-ink">Planned vs. Spent by Category</h2>
              <Link
                href="/distribution"
                className="text-sm font-medium text-rust-500 transition-colors duration-250 ease-ledger hover:text-rust-700"
              >
                Manage distribution &rarr;
              </Link>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {distribution.categories.map((category) => (
                <CategoryProgressBar key={category.id} category={category} currency={currency} />
              ))}
            </div>
          </section>

          {/* Spending vs planned + category chart */}
          <section className="grid gap-4 lg:grid-cols-[1fr_20rem]">
            <SpendingByCategoryChart data={summary.spending.spending_by_category} currency={currency} />
            <div className="rounded-md border border-line bg-card p-4 sm:p-5">
              <h3 className="font-display text-lg text-ink">Planned vs. Actual</h3>
              <p className="text-sm text-ink-soft">Total spending across every category</p>
              <dl className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <dt className="text-sm text-ink-soft">Planned</dt>
                  <dd>
                    <AmountDisplay value={summary.spending.planned_vs_actual.planned} currency={currency} size="sm" />
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-sm text-ink-soft">Actual</dt>
                  <dd>
                    <AmountDisplay value={summary.spending.planned_vs_actual.actual} currency={currency} size="sm" />
                  </dd>
                </div>
              </dl>
            </div>
          </section>

          {/* Savings */}
          <section>
            <h2 className="font-display text-xl text-ink">Saved</h2>
            <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-4">
              <Stat label="Saved Automatically" value={summary.savings.automatic_savings} currency={currency} tone="positive" />
              <Stat label="Saved Manually" value={summary.savings.manual_savings} currency={currency} tone="positive" />
              <Stat label="Total Saved" value={summary.savings.final_savings} currency={currency} tone="positive" emphasize />
              <Stat label="Sent to Accounts" value={summary.savings.distributed_savings} currency={currency} />
            </div>
            {!isZero(summary.savings.undistributed_savings) && (
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-saved-bg bg-saved-bg px-4 py-3">
                <p className="text-sm text-ink">
                  <span className="font-semibold text-saved">
                    <AmountDisplay value={summary.savings.undistributed_savings} currency={currency} size="sm" tone="neutral" />
                  </span>{" "}
                  hasn&apos;t been sent to an account or savings goal yet.
                </p>
                <Link
                  href="/savings"
                  className="text-sm font-semibold text-rust-500 transition-colors duration-250 ease-ledger hover:text-rust-700"
                >
                  Assign it &rarr;
                </Link>
              </div>
            )}
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
                  {account.institution_name} &middot; &bull;&bull;&bull;&bull; {account.account_identifier_last4}
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
