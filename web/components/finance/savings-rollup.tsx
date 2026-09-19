import { AmountDisplay } from "./amount-display";
import { isZero } from "@/lib/money";
import type { SavingsSummary } from "@/lib/types";

export interface SavingsRollupProps {
  summary: SavingsSummary;
  currency: string;
}

/**
 * The canonical savings formula, rendered exactly as the backend computed it
 * (spec §26: Automatic Savings + Manual Savings = Final Savings; Final Savings
 * - Savings Distributed = Undistributed Savings) — nothing here sums or
 * subtracts, it only displays four numbers the API already returned.
 * `undistributed_total` may be negative (D-023, spec §38) when more has been
 * sent to accounts than current savings cover; it's shown plainly, in the
 * same red used for an overspent category, never clamped to zero.
 *
 * Split out of app/(app)/savings/page.tsx as a pure, fixture-testable
 * component the same way `PeriodDistributionView` is (Phase 5 part 3
 * precedent) — this is the one piece of the Savings page a test can render
 * with plain props instead of mocking the API.
 */
export function SavingsRollup({ summary, currency }: SavingsRollupProps) {
  const shortfall = Number(summary.undistributed_total) < 0;
  const hasUndistributed = !isZero(summary.undistributed_total);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-4">
        <Stat label="Saved Automatically" value={summary.automatic_savings_computed} currency={currency} tone="positive" />
        <Stat label="Saved Manually" value={summary.manual_savings_total} currency={currency} tone="positive" />
        <Stat label="Total Saved" value={summary.final_savings_total} currency={currency} tone="positive" emphasize />
        <Stat label="Sent to Accounts" value={summary.distributed_total} currency={currency} />
      </div>

      {hasUndistributed && (
        <div
          className={
            "flex flex-wrap items-center justify-between gap-3 rounded-md border px-4 py-3 " +
            (shortfall ? "border-overspent-bg bg-overspent-bg/40" : "border-saved-bg bg-saved-bg")
          }
        >
          <p className="text-sm text-ink">
            <span className="font-semibold">
              <AmountDisplay value={summary.undistributed_total} currency={currency} size="sm" tone="auto" />
            </span>{" "}
            {shortfall
              ? "more has been sent to accounts than your current savings cover — review your recent allocations below."
              : "of this period's savings hasn't been sent to an account or destination yet."}
          </p>
        </div>
      )}
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
