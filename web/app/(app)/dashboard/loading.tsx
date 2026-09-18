import { DashboardLoadingSkeleton } from "./loading-skeleton";

// Next's App Router Suspense convention: shown automatically while the
// server component in page.tsx is resolving data (real API calls arrive in
// Phase 3). This is the idiomatic place for dashboard loading feedback,
// rather than an artificial client-side timer over data that's already
// resolved by the time it reaches the browser.
export default function Loading() {
  return <DashboardLoadingSkeleton />;
}
