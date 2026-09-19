// Fixture data for the anonymous landing page's ledger preview ONLY
// (app/page.tsx) — never fetched, never shown to a signed-in user, and not a
// stand-in for any real API response. Every authenticated page fetches real
// data via lib/api.ts (see Phase 5 part 1: dashboard, financial periods, and
// the app shell all read from the FastAPI backend now).
//
// Currency is GMD (Gambian Dalasi) and names reflect a Banjul-based household,
// per the product's target market — even a marketing fixture uses realistic
// data, not "Item 1/Item 2" (Design identity).

import type { DistributionView, LandingPreviewSummary } from "./types";

// Illustrative only — the real `/distribution` page (a later Phase 5 part) will
// need a backend endpoint that returns this same shape computed from real
// records; see the `DistributionView` doc comment in lib/types.ts for why that
// endpoint doesn't exist yet.
export const mockDistribution: DistributionView = {
  financial_period_id: "preview",
  total_allocation: "47100.0000",
  total_used: "31280.5000",
  total_remaining: "15819.5000",
  categories: [
    {
      id: "cat-needs",
      name: "Needs",
      percentage: "50.00",
      allocation: "23550.0000",
      used: "24290.0000",
      remaining: "-740.0000",
      is_overspent: true,
      contributes_to_automatic_savings: false,
      is_unallocated_bucket: false,
    },
    {
      id: "cat-wants",
      name: "Wants",
      percentage: "20.00",
      allocation: "9420.0000",
      used: "4979.0000",
      remaining: "4441.0000",
      is_overspent: false,
      contributes_to_automatic_savings: true,
      is_unallocated_bucket: false,
    },
  ],
};

export const mockLandingPreviewSummary: LandingPreviewSummary = {
  income: {
    total_monthly_income: "47100.0000",
  },
};
