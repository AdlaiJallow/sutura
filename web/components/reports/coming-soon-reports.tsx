interface ComingSoonReport {
  name: string;
  description: string;
}

// Matches `app/reports/router.py` on the backend exactly, in the same order the
// router declares them — every one of these 501s by deliberate design (the
// router's own docstring: "Phase 6 concern"), not by omission. Nothing here is
// a link, a button, or backed by client-side-computed data (CLAUDE.md: don't
// synthesize a report from data already on hand) — it's an honest list of
// what's not built yet, the same spirit as `PhaseStub` elsewhere in the app.
const COMING_SOON: ComingSoonReport[] = [
  { name: "Income Report", description: "A breakdown of every income record across a period." },
  { name: "Expense Report", description: "Every expense, grouped and filterable by category." },
  { name: "Distribution Report", description: "How this period's allocation compared category by category." },
  { name: "Savings Report", description: "A closer look at automatic vs. manual savings over time." },
  { name: "Bank Accounts Report", description: "Balances and activity across every account." },
  { name: "Planned vs. Actual", description: "Budgeted amounts next to what actually happened." },
  { name: "Historical Comparison", description: "Compare two or more periods side by side." },
];

/**
 * Honest about what isn't built yet, rather than a broken link or a
 * client-computed stand-in — see the `PhaseStub` component this deliberately
 * echoes the tone of, and CLAUDE.md's instruction not to fake a report the
 * backend hasn't implemented as one.
 */
export function ComingSoonReports() {
  return (
    <section className="mt-12">
      <h2 className="font-display text-xl text-ink">More reports, coming later</h2>
      <p className="mt-1 max-w-md text-sm text-ink-soft">
        The backend only builds the Monthly Summary report so far — these are planned for a later
        phase, not missing by accident.
      </p>
      <ul className="mt-4 divide-y divide-line overflow-hidden rounded-md border border-line">
        {COMING_SOON.map((report) => (
          <li key={report.name} className="flex flex-wrap items-center justify-between gap-3 bg-card px-4 py-3">
            <div>
              <p className="text-sm font-medium text-ink">{report.name}</p>
              <p className="text-xs text-ink-faint">{report.description}</p>
            </div>
            <span className="shrink-0 rounded-full bg-secondary px-2.5 py-0.5 text-[0.6875rem] font-semibold tracking-wideish text-ink-faint uppercase">
              Coming soon
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
