import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  title: string;
  message?: string;
  action?: ReactNode;
  className?: string;
}

/** Generic "nothing here yet" state for list-style pages (expenses, income,
 * transactions, ...) once they're built in Phase 3 — one shared shape instead
 * of every table re-inventing its own empty row. */
export function EmptyState({ title, message, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "rounded-md border border-dashed border-line bg-card px-6 py-12 text-center",
        className,
      )}
    >
      <h3 className="font-display text-lg text-ink">{title}</h3>
      {message && <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-soft">{message}</p>}
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}
