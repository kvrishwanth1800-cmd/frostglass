"use client";

import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis } from "recharts";

// Sparkline of daily request volume. Charts carry no decorative colour; the
// line uses the muted token, consistent with H.6.1 (colour is reserved for
// policy outcomes, and volume is not an outcome).
export function Sparkline({ data }: { data: { day: string; count: number }[] }) {
  if (data.length === 0) {
    return <div className="h-16 text-sm text-muted">No traffic in this window.</div>;
  }
  return (
    <div className="h-16 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="day" hide />
          <Tooltip
            contentStyle={{
              background: "var(--fg-raised)",
              border: "1px solid var(--fg-hairline)",
              color: "var(--fg-text)",
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="count"
            stroke="var(--fg-muted)"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
