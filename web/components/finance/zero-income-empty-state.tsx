import Link from "next/link";
import { Button } from "@/components/ui/button";

export interface ZeroIncomeEmptyStateProps {
  periodLabel: string;
}

/** Shown on the dashboard when a period has no salary, allowances, or other
 * income recorded yet — spec §38 edge case "zero income". Tells the person
 * exactly what to do next rather than showing a blank/broken-looking page. */
export function ZeroIncomeEmptyState({ periodLabel }: ZeroIncomeEmptyStateProps) {
  return (
    <div className="rounded-md border border-dashed border-line bg-card px-6 py-14 text-center">
      <p className="text-xs font-semibold tracking-wideish text-rust-500 uppercase">
        {periodLabel}
      </p>
      <h2 className="mx-auto mt-2 max-w-md font-display text-2xl text-ink">
        Nothing recorded for {periodLabel} yet
      </h2>
      <p className="mx-auto mt-2 max-w-sm text-sm text-ink-soft">
        Add your salary or income for this period and Sutura will work out your
        allocations, spending room, and savings automatically.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Button asChild>
          <Link href="/salary">Add salary</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/income">Add other income</Link>
        </Button>
      </div>
    </div>
  );
}
