// Plain-text label helpers — no financial math, just string formatting so enum
// values from the API (e.g. "FAMILY_SUPPORT") read as plain language (spec §33).

export function humanizeEnum(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function monthLabel(year: number, month: number): string {
  return `${MONTH_NAMES[month - 1] ?? month} ${year}`;
}
