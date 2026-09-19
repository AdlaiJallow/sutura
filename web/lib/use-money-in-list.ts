// Shared list-fetch boilerplate for the three money-in modules (salary,
// allowances, income — Phase 5 part 2). Each is "a period-scoped list of
// money-in records" (CLAUDE.md) and was re-fetching/erroring identically
// before this existed — this is that one shared piece rather than three
// copies of the same load/error/reload dance already seen on
// app/(app)/financial-periods/page.tsx.
"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";
import type { Paginated } from "./types";

export function useMoneyInList<T>(fetcher: () => Promise<Paginated<T>>) {
  const [records, setRecords] = useState<T[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRecords(null);
    setError(null);
    try {
      const res = await fetcher();
      setRecords(res.data);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong loading this. Please try again.",
      );
    }
  }, [fetcher]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  return { records, error, reload: load };
}
