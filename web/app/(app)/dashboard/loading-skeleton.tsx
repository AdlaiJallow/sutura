import { Skeleton } from "@/components/ui/skeleton";

/** Loading feedback for the dashboard's first paint (Design identity:
 * "purposeful micro-interactions ... loading feedback"). Shaped like the
 * real layout so nothing jumps once data resolves. */
export function DashboardLoadingSkeleton() {
  return (
    <div className="animate-fade-in space-y-10">
      <div>
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-3 h-12 w-72" />
        <Skeleton className="mt-2 h-4 w-48" />
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-36" />
        ))}
      </div>
      <Skeleton className="h-80" />
    </div>
  );
}
