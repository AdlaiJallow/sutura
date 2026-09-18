/**
 * The Sutura mark: a single gestural stroke tracing the brand's initial,
 * closed off by a rust full-stop — the same "one figure, one accent" rhythm
 * as the ledger's amount displays (ink for the number, rust only where it
 * needs your attention). Uses `currentColor` for the stroke so it can sit on
 * paper or ink backgrounds without a separate asset; the dot stays brand-rust
 * regardless of context, the way a single flagged line stays rust in a ledger
 * full of otherwise-neutral ink.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M66 22 C 40 22, 30 32, 30 42 C 30 56, 70 46, 70 60 C 70 72, 58 78, 34 76"
        stroke="currentColor"
        strokeWidth="12"
        strokeLinecap="round"
      />
      <circle cx="66" cy="22" r="6.5" fill="var(--color-rust-500, #c1502e)" />
    </svg>
  );
}
