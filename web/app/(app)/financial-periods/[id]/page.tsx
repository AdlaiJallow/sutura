import { PhaseStub } from "@/components/layout/phase-stub";

export default async function FinancialPeriodDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <PhaseStub
      title={`Period ${id}`}
      description="The full month, tab by tab: overview, income, expenses, distribution, savings, and accounts."
    />
  );
}
