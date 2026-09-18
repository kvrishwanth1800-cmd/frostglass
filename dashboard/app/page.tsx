"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { StatsOverview } from "@/lib/types";
import { formatCents, formatPct } from "@/lib/utils";
import { RangeTabs } from "@/components/range-tabs";
import { AppShell } from "@/components/app-shell";
import { LoadingState, ErrorState } from "@/components/states";
import { OutcomeLedger } from "@/components/overview/outcome-ledger";
import { Sparkline } from "@/components/overview/sparkline";
import { outcomeDotClass } from "@/components/ui/outcome";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded border border-hairline bg-raised p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-xl">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

function RankedList({
  title,
  rows,
}: {
  title: string;
  rows: { label: string; value: string; flagged?: number }[];
}) {
  return (
    <div className="rounded border border-hairline bg-raised p-4">
      <h3 className="mb-3 text-sm text-muted">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">Nothing in this window.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((row) => (
            <li key={row.label} className="flex items-center justify-between text-sm">
              <span className="truncate">{row.label}</span>
              <span className="font-mono text-muted">{row.value}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function OverviewPage() {
  const { session } = useSession();
  const [range, setRange] = useState("7d");
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setStats(null);
    setError(null);
    api
      .statsOverview(session.token, range)
      .then((data) => active && setStats(data))
      .catch((err: unknown) =>
        active && setError(err instanceof ApiError ? err.message : "Could not load overview."),
      );
    return () => {
      active = false;
    };
  }, [session.token, range]);

  return (
    <AppShell>
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl">Overview</h1>
          <p className="text-sm text-muted">What is crossing the boundary, and what happened to it.</p>
        </div>
        <RangeTabs value={range} onChange={setRange} />
      </header>

      <div className="flex flex-col gap-4">
        <OutcomeLedger />

        {error ? (
          <ErrorState message={error} onRetry={() => setRange((prev) => prev)} />
        ) : stats === null ? (
          <LoadingState label="Aggregating" />
        ) : (
          <>
            <ShadowBanner />

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <Stat label="Requests today" value={String(stats.totals.today)} />
              <Stat label="Last 7 days" value={String(stats.totals.last_7d)} />
              <Stat label="Last 30 days" value={String(stats.totals.last_30d)} />
              <Stat
                label="Contain sensitive data"
                value={formatPct(stats.sensitive_pct)}
                hint={`${stats.sensitive_requests} of ${stats.windowed_total} in window`}
              />
            </div>

            <div className="rounded border border-hairline bg-raised p-4">
              <h3 className="mb-2 text-sm text-muted">Daily volume ({range})</h3>
              <Sparkline data={stats.sparkline} />
            </div>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {["blocked", "masked", "shadow", "allowed"].map((outcome) => (
                <div key={outcome} className="rounded border border-hairline bg-raised p-4">
                  <p className="flex items-center gap-1.5 text-sm text-muted">
                    <span className={`h-2 w-2 rounded-full ${outcomeDotClass(outcome)}`} />
                    {outcome}
                  </p>
                  <p className="mt-1 text-xl">{stats.by_action[outcome] ?? 0}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <RankedList
                title="Top entity types"
                rows={stats.top_entity_types.map((row) => ({
                  label: row.entity_type,
                  value: String(row.count),
                }))}
              />
              <RankedList
                title="Top users by flagged volume"
                rows={stats.top_users.map((row) => ({
                  label: row.user,
                  value: `${row.flagged} flagged / ${row.count}`,
                }))}
              />
              <RankedList
                title="Top teams by flagged volume"
                rows={stats.top_teams.map((row) => ({
                  label: row.team,
                  value: `${row.flagged} flagged / ${row.count}`,
                }))}
              />
              <RankedList
                title="Spend by provider"
                rows={stats.spend_by_provider.map((row) => ({
                  label: row.provider,
                  value: formatCents(row.cost_cents),
                }))}
              />
              <RankedList
                title="Spend by model"
                rows={stats.spend_by_model.map((row) => ({
                  label: row.model,
                  value: formatCents(row.cost_cents),
                }))}
              />
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

// Persistent banner while any team is in shadow mode (H.6.2 page 1). It reads
// team shadow state from the Access API so the count is real, not inferred.
function ShadowBanner() {
  const { session } = useSession();
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => {
    let active = true;
    api
      .teams(session.token)
      .then((data) => active && setCount(data.items.filter((team) => team.shadow_mode).length))
      .catch(() => active && setCount(null));
    return () => {
      active = false;
    };
  }, [session.token]);
  if (!count) return null;
  return (
    <div className="rounded border border-shadow/40 bg-shadow/10 px-4 py-3 text-sm text-text">
      <span className="text-shadow">{count}</span>{" "}
      {count === 1 ? "team is" : "teams are"} in shadow mode - detections are logged but nothing is
      masked.
    </div>
  );
}
