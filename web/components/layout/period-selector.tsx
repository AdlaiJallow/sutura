"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "@/components/finance/status-badge";
import { usePeriod } from "./period-context";
import { monthLabel } from "@/lib/text";

/** Drives `financial_period_id` for every data-fetching page (frontend-routes.md
 * "PeriodSelector"). Lives in the app shell header so switching periods is
 * always one click away, wherever a person is in the app. */
export function PeriodSelector() {
  const { period, periods, setPeriodId } = usePeriod();

  return (
    <Select value={period.id} onValueChange={setPeriodId}>
      <SelectTrigger
        size="sm"
        className="figure gap-2 border-line bg-card text-sm data-[state=open]:border-rust-500"
        aria-label="Choose financial period"
      >
        <SelectValue>
          <span className="flex items-center gap-2">
            {monthLabel(period.year, period.month)}
            <StatusBadge status={period.status} />
          </span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent align="end">
        {periods.map((p) => (
          <SelectItem key={p.id} value={p.id} className="figure">
            <span className="flex w-full items-center justify-between gap-3">
              {monthLabel(p.year, p.month)}
              <StatusBadge status={p.status} />
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
