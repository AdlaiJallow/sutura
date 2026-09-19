import { AmountDisplay } from "@/components/finance/amount-display";
import { isZero } from "@/lib/money";
import { humanizeEnum, monthLabel } from "@/lib/text";
import type { FinancialPeriod, MonthlySummary } from "@/lib/types";

export interface MonthlySummaryReportProps {
  period: FinancialPeriod;
  summary: MonthlySummary;
}

function ReportRow({
  label,
  value,
  currency,
  indent = false,
  emphasize = false,
  tone = "neutral",
}: {
  label: string;
  value: string;
  currency: string;
  indent?: boolean;
  emphasize?: boolean;
  tone?: "neutral" | "positive" | "auto";
}) {
  return (
    <div
      className={
        "flex items-baseline justify-between gap-4 border-b border-dotted border-line py-2 " +
        (emphasize ? "border-b-0 border-t border-solid border-ink pt-3" : "")
      }
    >
      <span className={indent ? "pl-5 text-sm text-ink-soft" : "text-sm text-ink"}>{label}</span>
      <AmountDisplay
        value={value}
        currency={currency}
        tone={tone}
        weight={emphasize ? "semibold" : "medium"}
        size={emphasize ? "lg" : "sm"}
      />
    </div>
  );
}

/**
 * The one real report the backend implements (spec: `GET
 * /reports/monthly-summary/{period_id}` reuses the same authoritative cache
 * row the dashboard reads, spec §26/§27 — nothing here is re-derived, every
 * figure is exactly what `MonthlySummary` already carries). Deliberately
 * styled as a document rather than the dashboard's stat-grid: a report is
 * something you'd print or hand to someone else, so it reads top-to-bottom
 * like a statement instead of a scannable at-a-glance card layout.
 */
export function MonthlySummaryReport({ period, summary }: MonthlySummaryReportProps) {
  const currency = period.base_currency;
  const label = monthLabel(period.year, period.month);
  const hasIncome = !isZero(summary.total_monthly_income);
  const hasUndistributed = !isZero(summary.undistributed_savings);

  return (
    <article className="rounded-md border border-line bg-paper-raised p-6 shadow-card sm:p-10 print:border-0 print:p-0 print:shadow-none">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-ink pb-4">
        <div>
          <p className="text-xs font-semibold tracking-wideish text-rust-500 uppercase">
            Monthly Summary Report
          </p>
          <h1 className="mt-1 font-display text-2xl text-ink sm:text-3xl">{label}</h1>
        </div>
        <div className="text-right text-xs text-ink-faint">
          <p>{period.start_date} to {period.end_date}</p>
          <p className="mt-0.5">
            {period.status === "OPEN"
              ? "Recalculated live as you add records."
              : "Frozen at the numbers this period had when it was closed."}
          </p>
        </div>
      </header>

      {!hasIncome && (
        <p className="mt-4 rounded-md bg-secondary px-4 py-3 text-sm text-ink-soft">
          No income has been recorded for {label} yet, so every figure below is zero.
        </p>
      )}

      <section className="mt-6">
        <h2 className="text-xs font-semibold tracking-wideish text-ink-faint uppercase">Income</h2>
        <div className="mt-2">
          <ReportRow label="Salary & Allowances" value={summary.total_salary_income} currency={currency} />
          <ReportRow
            label="of which, Allowances"
            value={summary.total_allowances}
            currency={currency}
            indent
          />
          <ReportRow label="Other Income" value={summary.total_other_income} currency={currency} />
          <ReportRow
            label="Total Monthly Income"
            value={summary.total_monthly_income}
            currency={currency}
            emphasize
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-xs font-semibold tracking-wideish text-ink-faint uppercase">
          Spending & Savings
        </h2>
        <div className="mt-2">
          <ReportRow label="Spent This Period" value={summary.total_expenses} currency={currency} />
          <ReportRow label="Planned Savings" value={summary.total_planned_savings} currency={currency} />
          <ReportRow
            label="Saved Automatically"
            value={summary.automatic_savings}
            currency={currency}
            tone="positive"
          />
          <ReportRow
            label="Saved Manually"
            value={summary.manual_savings}
            currency={currency}
            tone="positive"
          />
          <ReportRow
            label="Final Savings"
            value={summary.final_savings}
            currency={currency}
            tone="positive"
            emphasize
          />
          <ReportRow
            label="Sent to Bank Accounts"
            value={summary.total_bank_deposits}
            currency={currency}
          />
          <ReportRow
            label="Undistributed Savings"
            value={summary.undistributed_savings}
            currency={currency}
            tone="auto"
          />
        </div>
        {hasUndistributed && (
          <p className="mt-2 text-xs text-ink-faint">
            {Number(summary.undistributed_savings) < 0
              ? "Negative means more has been sent to accounts than this period's savings currently cover."
              : "This is savings that hasn't been sent to an account or destination yet."}
          </p>
        )}
      </section>

      <footer className="mt-8 border-t border-line pt-4 text-xs text-ink-faint">
        Calculated {new Date(summary.calculated_at).toLocaleString("en-GB")} ·{" "}
        {humanizeEnum(summary.triggered_by)} · version {summary.version}
        {!summary.is_current && " · a newer calculation exists for this period"}
      </footer>
    </article>
  );
}
