"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "./chart-card";
import { formatMoney, parseMoney } from "@/lib/money";
import { humanizeEnum } from "@/lib/text";

export interface SpendingByCategoryChartProps {
  data: { category: string; amount: string }[];
  currency?: string;
}

/**
 * Renders the API-provided `spending_by_category` breakdown (already an
 * aggregate from the backend, never re-summed here) as a horizontal bar
 * chart. Amount strings are parsed to numbers only because Recharts requires
 * a numeric axis — the figures shown in the tooltip/axis are the same values
 * the API returned, just formatted (lib/money.ts), never combined.
 */
export function SpendingByCategoryChart({
  data,
  currency = "GMD",
}: SpendingByCategoryChartProps) {
  if (data.length === 0) {
    return (
      <ChartCard title="Spending by category" subtitle="Where this period's money went">
        <p className="py-8 text-center text-sm text-ink-faint">
          No expenses recorded yet this period.
        </p>
      </ChartCard>
    );
  }

  const chartData = [...data]
    .map((row) => ({ label: humanizeEnum(row.category), amount: parseMoney(row.amount) }))
    .sort((a, b) => b.amount - a.amount);

  return (
    <ChartCard title="Spending by category" subtitle="Where this period's money went">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
            <CartesianGrid horizontal={false} stroke="var(--line)" />
            <XAxis
              type="number"
              tickFormatter={(v: number) => formatMoney(String(v), currency)}
              tick={{ fill: "var(--ink-soft, #5B4E40)", fontSize: 11, fontFamily: "var(--font-work-sans)" }}
              axisLine={{ stroke: "var(--line)" }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={120}
              tick={{ fill: "#241C14", fontSize: 12, fontFamily: "var(--font-work-sans)" }}
              axisLine={{ stroke: "var(--line)" }}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(193, 80, 46, 0.06)" }}
              formatter={(value) => formatMoney(String(value ?? 0), currency)}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #E4D9C6",
                fontFamily: "var(--font-work-sans)",
                fontSize: 12,
              }}
            />
            <Bar dataKey="amount" fill="#C1502E" radius={[0, 4, 4, 0]} maxBarSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}
