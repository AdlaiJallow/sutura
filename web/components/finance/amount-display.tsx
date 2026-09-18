import { cn } from "@/lib/utils";
import { formatMoney, isNegative } from "@/lib/money";
import type { Money } from "@/lib/types";

type Tone = "neutral" | "positive" | "negative" | "auto";
type Size = "xs" | "sm" | "md" | "lg" | "xl";

const sizeClasses: Record<Size, string> = {
  xs: "text-xs",
  sm: "text-sm",
  md: "text-base",
  lg: "text-2xl",
  xl: "text-4xl md:text-5xl",
};

const toneClasses: Record<Exclude<Tone, "auto">, string> = {
  neutral: "text-ink",
  positive: "text-ontrack",
  negative: "text-overspent",
};

export interface AmountDisplayProps {
  /** A Decimal-as-string value exactly as returned by the API. Never a number. */
  value: Money;
  currency?: string;
  size?: Size;
  /**
   * "auto" colors the figure red when the API value itself is negative
   * (e.g. an overspent remaining balance) — it never inspects or compares
   * against any other figure, it only reads the sign already on this value.
   */
  tone?: Tone;
  weight?: "normal" | "medium" | "semibold";
  className?: string;
  as?: "span" | "div";
}

/**
 * The only place a Money string is turned into on-screen digits. Every page
 * renders amounts through this component (never its own Intl call, never its
 * own arithmetic) so the ledger-mono treatment and sign handling stay
 * consistent everywhere (frontend-routes.md "AmountDisplay").
 */
export function AmountDisplay({
  value,
  currency = "GMD",
  size = "md",
  tone = "neutral",
  weight = "medium",
  className,
  as = "span",
}: AmountDisplayProps) {
  const resolvedTone: Exclude<Tone, "auto"> =
    tone === "auto" ? (isNegative(value) ? "negative" : "neutral") : tone;
  const Comp = as;

  return (
    <Comp
      className={cn(
        "figure inline-block whitespace-nowrap",
        sizeClasses[size],
        toneClasses[resolvedTone],
        weight === "semibold" && "font-semibold",
        weight === "medium" && "font-medium",
        className,
      )}
    >
      {formatMoney(value, currency)}
    </Comp>
  );
}
