export interface PhaseStubProps {
  title: string;
  description: string;
  phase?: string;
}

/**
 * Shared placeholder body for routes not yet built out (spec §47 build
 * order — Foundation now, Financial Core UI in Phase 3, the rest in Phase 5).
 * Every stub route renders through this so the "coming soon" pattern isn't
 * duplicated per page, and so the eventual real page swaps in without
 * touching the surrounding shell/nav.
 */
export function PhaseStub({ title, description, phase = "Phase 5" }: PhaseStubProps) {
  return (
    <div className="mx-auto max-w-2xl py-16 text-center">
      <p className="text-xs font-semibold tracking-wideish text-rust-500 uppercase">
        Coming in {phase}
      </p>
      <h1 className="mt-2 font-display text-3xl text-ink">{title}</h1>
      <p className="mx-auto mt-3 max-w-md text-sm text-ink-soft">{description}</p>
    </div>
  );
}
