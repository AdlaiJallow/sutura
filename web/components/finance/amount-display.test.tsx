import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AmountDisplay } from "./amount-display";

describe("<AmountDisplay />", () => {
  it("renders a zero-income value without crashing", () => {
    render(<AmountDisplay value="0.0000" currency="GMD" />);
    expect(screen.getByText("GMD 0.00")).toBeInTheDocument();
  });

  it("renders a positive figure with the currency code", () => {
    render(<AmountDisplay value="47100.0000" currency="GMD" />);
    expect(screen.getByText("GMD 47,100.00")).toBeInTheDocument();
  });

  it("colors an overspent (negative) figure using the overspent tone", () => {
    render(<AmountDisplay value="-740.0000" currency="GMD" tone="negative" />);
    const el = screen.getByText("-GMD 740.00");
    expect(el.className).toContain("text-overspent");
  });

  it("auto tone reads the sign from the value itself, not from a comparison", () => {
    render(<AmountDisplay value="-1.0000" currency="GMD" tone="auto" />);
    expect(screen.getByText("-GMD 1.00").className).toContain("text-overspent");
  });
});
