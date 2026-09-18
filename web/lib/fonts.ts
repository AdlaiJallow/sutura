import { Fraunces, Work_Sans, IBM_Plex_Mono } from "next/font/google";

// Display serif — editorial weight for headings, big figures, and the wordmark.
// Variable weight is required alongside `axes` (opsz/SOFT/WONK) — Next.js's font
// loader rejects axes on a fixed weight list.
export const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  axes: ["opsz", "SOFT", "WONK"],
  weight: "variable",
  display: "swap",
});

// Body / UI grotesk — quiet, legible, does the everyday reading work.
export const workSans = Work_Sans({
  subsets: ["latin"],
  variable: "--font-work-sans",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

// Ledger mono — every amount, date, and account number renders in this so
// figures line up like a real ledger (tabular figures, no ambiguity between
// currency symbol and digits).
export const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-plex-mono",
  weight: ["400", "500", "600"],
  display: "swap",
});
