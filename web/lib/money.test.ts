import { describe, expect, it } from "vitest";
import { formatMoney, isNegative, isZero, parseMoney } from "./money";

describe("money formatting helpers (presentation only — no arithmetic)", () => {
  it("formats a Decimal-as-string API value with grouping and two decimals", () => {
    expect(formatMoney("47100.0000", "GMD")).toBe("GMD 47,100.00");
  });

  it("formats a zero-income value without throwing", () => {
    expect(formatMoney("0.0000", "GMD")).toBe("GMD 0.00");
  });

  it("keeps a negative remaining balance visible instead of clamping to zero", () => {
    expect(formatMoney("-740.0000", "GMD")).toBe("-GMD 740.00");
  });

  it("detects negative and zero values from the raw API string", () => {
    expect(isNegative("-740.0000")).toBe(true);
    expect(isNegative("740.0000")).toBe(false);
    expect(isZero("0.0000")).toBe(true);
    expect(isZero("0.0100")).toBe(false);
  });

  it("falls back to 0 for a malformed value rather than crashing", () => {
    expect(parseMoney("not-a-number")).toBe(0);
  });
});
