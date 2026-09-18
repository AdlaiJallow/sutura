"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

/** Generic "something went wrong" state for any page that fetches from the
 * API — reused instead of every route writing its own error copy/markup. */
export function ErrorState({
  title = "Couldn't load this page",
  message = "Something went wrong talking to the Sutura server. Your data is safe — try again in a moment.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-md border border-overspent-bg bg-overspent-bg/40 px-6 py-10 text-center",
        className,
      )}
    >
      <h2 className="font-display text-xl text-overspent">{title}</h2>
      <p className="mx-auto mt-2 max-w-sm text-sm text-ink-soft">{message}</p>
      {onRetry && (
        <Button variant="outline" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
