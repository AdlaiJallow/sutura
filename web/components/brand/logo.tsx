import { LogoMark } from "./logo-mark";

const SIZES = {
  sm: { mark: "size-5", text: "text-base" },
  md: { mark: "size-6", text: "text-xl" },
  lg: { mark: "size-8", text: "text-2xl" },
} as const;

/**
 * The wordmark lockup used everywhere "Sutura" appears as a brand name
 * (header, auth screens). `tone="reverse"` is for the ink-background auth
 * cover — the mark's stroke follows `currentColor`, so only the text color
 * needs to flip, the rust dot stays put.
 */
export function Logo({
  size = "md",
  tone = "default",
  className,
}: {
  size?: keyof typeof SIZES;
  tone?: "default" | "reverse";
  className?: string;
}) {
  const { mark, text } = SIZES[size];
  return (
    <span
      className={`inline-flex items-center gap-2 ${tone === "reverse" ? "text-paper" : "text-ink"} ${className ?? ""}`}
    >
      <LogoMark className={mark} />
      <span className={`font-display font-semibold tracking-tightish ${text}`}>Sutura</span>
    </span>
  );
}
