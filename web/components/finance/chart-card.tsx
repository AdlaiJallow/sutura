import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface ChartCardProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Consistent frame (title, subtitle, axis/legend spacing) for every Recharts
 * chart in the app — /dashboard and /analytics both wrap charts in this so no
 * page hand-rolls its own chart chrome (frontend-routes.md "ChartCard"). */
export function ChartCard({ title, subtitle, action, children, className }: ChartCardProps) {
  return (
    <div className={cn("rounded-md border border-line bg-card p-4 sm:p-5", className)}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg text-ink">{title}</h3>
          {subtitle && <p className="text-sm text-ink-soft">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}
