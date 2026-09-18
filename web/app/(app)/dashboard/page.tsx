import { DashboardView } from "./dashboard-view";
import {
  mockBankAccounts,
  mockCurrentPeriod,
  mockDistribution,
  mockPeriodSummary,
  mockZeroDistribution,
  mockZeroIncomePeriodSummary,
} from "@/lib/mock-data";

// Spec §21: income, distribution, spending-vs-planned, savings, and account
// balances in one view, all straight from `GET /financial-periods/{id}/summary`,
// `GET /distributions/{period_id}`, and `GET /bank-accounts` once Phase 3 wires
// the real API in — this page swaps the mock fixtures below for those calls
// without touching DashboardView's props.
//
// `?empty=1` demonstrates the zero-income edge case (spec §38) against the
// same layout, for local verification without a backend.
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const isZeroDemo = params.empty === "1";

  return (
    <DashboardView
      period={mockCurrentPeriod}
      summary={isZeroDemo ? mockZeroIncomePeriodSummary : mockPeriodSummary}
      distribution={isZeroDemo ? mockZeroDistribution : mockDistribution}
      accounts={isZeroDemo ? [] : mockBankAccounts}
    />
  );
}
