// Presentation-only helpers for rendering API-provided Decimal-as-string values
// (see lib/types.ts `Money`). Nothing in this file sums, multiplies, allocates,
// or otherwise derives a new financial figure — it only changes how an
// already-computed backend value is displayed (sign, grouping, decimals).
// See CLAUDE.md / frontend-engineer.md: the backend is the sole source of truth
// for every computed number.

/** Parses a Decimal-as-string API value for *display formatting only*. */
export function parseMoney(value: string): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export function isNegative(value: string): boolean {
  return parseMoney(value) < 0;
}

export function isZero(value: string): boolean {
  return parseMoney(value) === 0;
}

/**
 * Formats a Money string as "GMD 1,234.00" (or "-GMD 740.00" for a negative
 * remaining balance — shown as-is, never clamped to zero, per spec §33/§38).
 */
export function formatMoney(value: string, currency = "GMD"): string {
  const n = parseMoney(value);
  const formatted = new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(n));
  const sign = n < 0 ? "-" : "";
  return `${sign}${currency} ${formatted}`;
}

/** Formats an ISO date ("2026-09-14") as "14 Sep 2026" for the ledger mono columns. */
export function formatLedgerDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(d);
}
