"use client";

import { useCallback, useEffect, useState } from "react";
import { DistributionRulesManager } from "@/components/finance/distribution-rule-manager";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePeriod } from "@/components/layout/period-context";
import { api, ApiError } from "@/lib/api";
import { monthLabel } from "@/lib/text";
import { useDistributionView } from "@/lib/use-distribution-view";
import { PeriodDistributionView } from "./period-distribution-view";
import type { DistributionRule } from "@/lib/types";

/**
 * Two distinct concerns, one page (spec §32): the live, server-computed
 * breakdown for the currently-selected financial period ("This period" —
 * `GET /distributions/{period_id}`, rendered by `PeriodDistributionView`),
 * and CRUD for the reusable rule *definitions* ("Manage rules" —
 * `components/finance/distribution-rule-manager.tsx`). A controlled `Tabs`
 * (not a sub-route) so "Create your first rule" from the empty state can
 * jump straight to the second tab without a navigation.
 */
export default function DistributionPage() {
  const { period, refresh: refreshShellPeriods } = usePeriod();
  const { view, error: viewError, loading: viewLoading, reload: reloadView } = useDistributionView(period.id);
  const [tab, setTab] = useState<"period" | "rules">("period");

  const [rules, setRules] = useState<DistributionRule[] | null>(null);
  const [rulesError, setRulesError] = useState<string | null>(null);

  const loadRules = useCallback(async () => {
    setRulesError(null);
    try {
      const res = await api.distributionRules.list({ is_active: true, page_size: 100 });
      setRules(res.data);
    } catch (err) {
      setRulesError(
        err instanceof ApiError ? err.message : "Couldn't load your distribution rules.",
      );
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await loadRules();
    })();
  }, [loadRules]);

  async function handleRuleApplied() {
    await Promise.all([reloadView(), refreshShellPeriods()]);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Distribution</h1>
        <p className="mt-1 max-w-lg text-sm text-ink-soft">
          Decide what share of {monthLabel(period.year, period.month)}&apos;s income goes to each
          category, and see exactly what&apos;s left in each one.
        </p>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "period" | "rules")}>
        <TabsList variant="line">
          <TabsTrigger value="period">This period</TabsTrigger>
          <TabsTrigger value="rules">Manage rules</TabsTrigger>
        </TabsList>

        <TabsContent value="period" className="mt-6">
          <PeriodDistributionView
            period={period}
            view={view}
            error={viewError}
            loading={viewLoading}
            onReload={reloadView}
            rules={rules}
            rulesError={rulesError}
            onRuleApplied={handleRuleApplied}
            onCreateRule={() => setTab("rules")}
          />
        </TabsContent>

        <TabsContent value="rules" className="mt-6">
          <DistributionRulesManager onRulesChanged={loadRules} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
