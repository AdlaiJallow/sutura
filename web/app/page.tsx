import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AmountDisplay } from "@/components/finance/amount-display";
import { CategoryProgressBar } from "@/components/finance/category-progress-bar";
import { mockDistribution, mockLandingPreviewSummary } from "@/lib/mock-data";

// Anonymous entry point. Once auth sessions exist (Phase 3), this becomes a
// server-side redirect — authenticated -> /dashboard, unauthenticated ->
// /login (frontend-routes.md) — but with no session to check yet, it does
// double duty as the product's first impression, so it gets real design
// attention now rather than staying a bare redirect stub.
const WORKFLOW = [
  { step: "Salary & income", detail: "Net salary, allowances, and anything else that comes in." },
  { step: "Distribution", detail: "You decide the percentages. Needs, Wants, Savings, your own categories." },
  { step: "Spending", detail: "Every expense lands against a category, so overspending shows immediately." },
  { step: "Savings", detail: "What's left over — automatic and manual — adds up on its own." },
  { step: "Bank accounts", detail: "Send savings to real accounts and watch balances stay in sync." },
];

export default function LandingPage() {
  const previewCategories = mockDistribution.categories.slice(0, 2);

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <span className="font-display text-xl font-semibold tracking-tightish text-ink">
            Sutura
          </span>
          <nav className="flex items-center gap-3">
            <Link href="/login" className="text-sm font-medium text-ink-soft hover:text-ink">
              Sign in
            </Link>
            <Button asChild size="sm">
              <Link href="/register">Create account</Link>
            </Button>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:items-center lg:py-24">
          <div>
            <p className="text-xs font-semibold tracking-wideish text-rust-500 uppercase">
              Personal finance, in plain language
            </p>
            <h1 className="mt-3 font-display text-5xl leading-[1.05] text-ink text-balance md:text-6xl">
              Know where every dalasi goes.
            </h1>
            <p className="mt-5 max-w-md text-base text-ink-soft">
              Sutura turns your salary, allowances, and other income into a clear monthly plan —
              what&apos;s allocated, what&apos;s spent, and what&apos;s saved. No spreadsheets, no
              accounting jargon.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/register">Create your free account</Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/login">I already have one</Link>
              </Button>
            </div>
          </div>

          {/* A real preview of the ledger, not a generic screenshot mockup. */}
          <div className="rounded-lg border border-line bg-card p-5 shadow-raised sm:p-6">
            <p className="text-xs font-semibold tracking-wideish text-ink-faint uppercase">
              September 2026 &middot; Money Available
            </p>
            <AmountDisplay
              value={mockLandingPreviewSummary.income.total_monthly_income}
              size="xl"
              weight="semibold"
              className="mt-1"
            />
            <div className="mt-5 space-y-3">
              {previewCategories.map((category) => (
                <CategoryProgressBar key={category.id} category={category} />
              ))}
            </div>
          </div>
        </section>

        <section className="border-t border-line bg-paper-sunken/60">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
            <h2 className="font-display text-3xl text-ink">How the money moves</h2>
            <ol className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
              {WORKFLOW.map((item, i) => (
                <li key={item.step} className="rounded-md border border-line bg-card p-4">
                  <span className="figure text-xs text-rust-500">{String(i + 1).padStart(2, "0")}</span>
                  <p className="mt-2 font-display text-lg text-ink">{item.step}</p>
                  <p className="mt-1 text-sm text-ink-soft">{item.detail}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </main>

      <footer className="border-t border-line px-4 py-6 text-center text-xs text-ink-faint sm:px-6">
        Sutura &middot; built for households, not accountants.
      </footer>
    </div>
  );
}
