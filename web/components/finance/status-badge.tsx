import { cn } from "@/lib/utils";

export type FinanceStatus =
  | "OPEN"
  | "CLOSED"
  | "ON_TRACK"
  | "OVERSPENT"
  | "UNDISTRIBUTED"
  | "RECURRING"
  | "MODIFIED"
  | "UNALLOCATED"
  | "AUTO"
  | "MANUAL"
  | "ACTIVE"
  | "INACTIVE";

const STATUS_CONFIG: Record<FinanceStatus, { label: string; className: string }> = {
  OPEN: { label: "Open", className: "bg-planned-bg text-planned" },
  CLOSED: { label: "Closed", className: "bg-secondary text-ink-soft" },
  ON_TRACK: { label: "On track", className: "bg-ontrack-bg text-ontrack" },
  OVERSPENT: { label: "Overspent", className: "bg-overspent-bg text-overspent" },
  UNDISTRIBUTED: { label: "Undistributed", className: "bg-saved-bg text-saved" },
  RECURRING: { label: "Recurring", className: "bg-secondary text-ink-soft" },
  MODIFIED: { label: "Modified since close", className: "bg-overspent-bg text-overspent" },
  UNALLOCATED: { label: "Unallocated", className: "bg-secondary text-ink-soft" },
  AUTO: { label: "Auto", className: "bg-planned-bg text-planned" },
  MANUAL: { label: "Manual", className: "bg-secondary text-ink-soft" },
  ACTIVE: { label: "Active", className: "bg-ontrack-bg text-ontrack" },
  INACTIVE: { label: "Inactive", className: "bg-secondary text-ink-faint" },
};

export interface StatusBadgeProps {
  status: FinanceStatus;
  className?: string;
}

/** Consistent Open/Closed/Overspent/Recurring/Modified treatment everywhere
 * a record's state needs to be shown at a glance (frontend-routes.md "StatusBadge"). */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold tracking-wideish uppercase",
        cfg.className,
        className,
      )}
    >
      <span className="size-1.5 shrink-0 rounded-full bg-current" aria-hidden />
      {cfg.label}
    </span>
  );
}
