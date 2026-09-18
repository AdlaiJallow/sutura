import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardView } from "./dashboard-view";
import {
  mockCurrentPeriod,
  mockZeroDistribution,
  mockZeroIncomePeriodSummary,
} from "@/lib/mock-data";

describe("<DashboardView /> — zero income edge case (spec §38)", () => {
  it("renders the zero-income empty state instead of crashing or showing blank sections", async () => {
    render(
      <DashboardView
        period={mockCurrentPeriod}
        summary={mockZeroIncomePeriodSummary}
        distribution={mockZeroDistribution}
        accounts={[]}
      />,
    );

    // The dashboard shows a brief loading skeleton before revealing content.
    expect(
      await screen.findByText(/Nothing recorded for/i, {}, { timeout: 2000 }),
    ).toBeInTheDocument();

    // It still tells the person what to do next rather than leaving a blank page.
    expect(screen.getByRole("link", { name: /add salary/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /add other income/i })).toBeInTheDocument();

    // No accounts recorded either — the accounts section should say so plainly.
    expect(screen.getByText(/no accounts added yet/i)).toBeInTheDocument();
  });
});
