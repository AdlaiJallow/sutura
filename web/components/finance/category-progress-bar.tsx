import Link from "next/link";
import { cn } from "@/lib/utils";
import { AmountDisplay } from "./amount-display";
import { StatusBadge } from "./status-badge";
import type { DistributionCategorySummary } from "@/lib/types";

export interface CategoryProgressBarProps {
  category: DistributionCategorySummary;
  currency?: string;
  /** When present, the whole card links to the category's items (e.g. /distribution). */
  href?: string;
  className?: string;
}

/**
 * Allocated / Used / Remaining bar for one distribution category. All amounts
 * shown are exactly what `GET /distributions/{period_id}` returned — this
 * component reads `is_overspent` from the API rather than comparing numbers
 * itself (spec §13, §46). The only client-side arithmetic here is the fill
 * ratio used to size the bar visually (like any chart/progress element must);
 * it is never rendered as a figure, and it never feeds a displayed amount.
 */
export function CategoryProgressBar({
  category,
  currency = "GMD",
  href,
  className,
}: CategoryProgressBarProps) {
  const allocation = Number(category.allocation);
  const used = Number(category.used);
  const fillRatio =
    allocation > 0 ? Math.min(used / allocation, 1) : used > 0 ? 1 : 0;
  const overflowRatio =
    allocation > 0 && used > allocation
      ? Math.min((used - allocation) / allocation, 1)
      : 0;

  const body = (
    <div
      className={cn(
        "rounded-md border border-line bg-card p-4 transition-colors duration-250 ease-ledger",
        href && "hover:border-ink-faint",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-display text-lg leading-tight text-ink">{category.name}</h3>
          {category.is_unallocated_bucket && <StatusBadge status="UNALLOCATED" />}
          {category.is_overspent && <StatusBadge status="OVERSPENT" />}
          {category.contributes_to_automatic_savings && (
            <span className="text-[0.6875rem] font-medium tracking-wideish text-ink-faint uppercase">
              feeds savings
            </span>
          )}
        </div>
        <span className="figure shrink-0 text-xs text-ink-faint">{category.percentage}%</span>
      </div>

      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-paper-sunken">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-250 ease-ledger",
            category.is_overspent ? "bg-overspent" : "bg-ontrack",
          )}
          style={{ width: `${fillRatio * 100}%` }}
        />
      </div>
      {category.is_overspent && (
        <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-overspent-bg" aria-hidden>
          <div
            className="h-full rounded-full bg-overspent"
            style={{ width: `${Math.max(overflowRatio, 0.1) * 100}%` }}
          />
        </div>
      )}

      <dl className="mt-3 grid grid-cols-3 gap-2">
        <div>
          <dt className="text-[0.6875rem] tracking-wideish text-ink-faint uppercase">Planned</dt>
          <dd>
            <AmountDisplay value={category.allocation} currency={currency} size="sm" />
          </dd>
        </div>
        <div>
          <dt className="text-[0.6875rem] tracking-wideish text-ink-faint uppercase">Spent</dt>
          <dd>
            <AmountDisplay value={category.used} currency={currency} size="sm" />
          </dd>
        </div>
        <div>
          <dt className="text-[0.6875rem] tracking-wideish text-ink-faint uppercase">Remaining</dt>
          <dd>
            <AmountDisplay
              value={category.remaining}
              currency={currency}
              size="sm"
              tone={category.is_overspent ? "negative" : "positive"}
            />
          </dd>
        </div>
      </dl>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block focus-visible:outline-none">
        {body}
      </Link>
    );
  }
  return body;
}
