import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ComingSoonReports } from "./coming-soon-reports";

afterEach(cleanup);

describe("<ComingSoonReports /> — honest about what isn't built yet", () => {
  it("lists every report type the backend 501s on, each marked Coming soon", () => {
    render(<ComingSoonReports />);

    for (const name of [
      "Income Report",
      "Expense Report",
      "Distribution Report",
      "Savings Report",
      "Bank Accounts Report",
      "Planned vs. Actual",
      "Historical Comparison",
    ]) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
    expect(screen.getAllByText("Coming soon")).toHaveLength(7);
  });

  it("never renders these as clickable links", () => {
    render(<ComingSoonReports />);
    expect(screen.queryAllByRole("link")).toHaveLength(0);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});
