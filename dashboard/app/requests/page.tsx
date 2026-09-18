"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { FindingView, RequestView } from "@/lib/types";
import { formatCents, formatTs } from "@/lib/utils";
import { AppShell } from "@/components/app-shell";
import { RangeTabs } from "@/components/range-tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Drawer } from "@/components/ui/dialog";
import { OutcomeChip } from "@/components/ui/outcome";
import { LoadingState, ErrorState, EmptyState } from "@/components/states";

const columnHelper = createColumnHelper<RequestView>();

const OUTCOME_FILTERS = ["all", "blocked", "masked", "shadow", "allowed"] as const;

function toCsv(rows: RequestView[]): string {
  const header = [
    "id",
    "ts",
    "user",
    "team",
    "model",
    "provider",
    "action",
    "prompt_tokens",
    "completion_tokens",
    "cost_cents",
    "latency_ms",
  ];
  const lines = rows.map((row) =>
    [
      row.id,
      row.ts,
      row.user,
      row.team,
      row.model,
      row.provider,
      row.action,
      row.prompt_tokens ?? "",
      row.completion_tokens ?? "",
      row.cost_cents ?? "",
      row.latency_ms ?? "",
    ].join(","),
  );
  return [header.join(","), ...lines].join("\n");
}

export default function RequestsPage() {
  const { session } = useSession();
  const [rows, setRows] = useState<RequestView[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [outcome, setOutcome] = useState<(typeof OUTCOME_FILTERS)[number]>("all");
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<RequestView | null>(null);

  useEffect(() => {
    let active = true;
    setRows(null);
    setError(null);
    setNextCursor(null);
    api
      .requests(session.token, { limit: 100, action: outcome === "all" ? undefined : outcome })
      .then((page) => {
        if (!active) return;
        setRows(page.items);
        setNextCursor(page.next_cursor);
      })
      .catch((err: unknown) =>
        active && setError(err instanceof ApiError ? err.message : "Could not load requests."),
      );
    return () => {
      active = false;
    };
  }, [session.token, outcome]);

  const loadMore = async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await api.requests(session.token, {
        limit: 100,
        cursor: nextCursor,
        action: outcome === "all" ? undefined : outcome,
      });
      setRows((prev) => [...(prev ?? []), ...page.items]);
      setNextCursor(page.next_cursor);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load more.");
    } finally {
      setLoadingMore(false);
    }
  };

  const filtered = useMemo(() => {
    const base = rows ?? [];
    if (!text.trim()) return base;
    const needle = text.toLowerCase();
    return base.filter((row) =>
      [row.user, row.team, row.model, row.provider, row.id].some((field) =>
        field.toLowerCase().includes(needle),
      ),
    );
  }, [rows, text]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("ts", {
        header: "Timestamp",
        cell: (info) => <span className="font-mono text-muted">{formatTs(info.getValue())}</span>,
      }),
      columnHelper.accessor("user", { header: "User" }),
      columnHelper.accessor("team", { header: "Team" }),
      columnHelper.accessor("model", {
        header: "Model",
        cell: (info) => <span className="font-mono">{info.getValue()}</span>,
      }),
      columnHelper.accessor("provider", { header: "Provider" }),
      columnHelper.accessor("action", {
        header: "Action",
        cell: (info) => <OutcomeChip outcome={info.getValue()} />,
      }),
      columnHelper.accessor("prompt_tokens", {
        header: "Tokens",
        cell: (info) => (
          <span className="font-mono text-muted">
            {(info.row.original.prompt_tokens ?? 0) + (info.row.original.completion_tokens ?? 0)}
          </span>
        ),
      }),
      columnHelper.accessor("cost_cents", {
        header: "Cost",
        cell: (info) => <span className="font-mono text-muted">{formatCents(info.getValue())}</span>,
      }),
      columnHelper.accessor("latency_ms", {
        header: "Latency",
        cell: (info) => (
          <span className="font-mono text-muted">
            {info.getValue() === null ? "-" : `${info.getValue()} ms`}
          </span>
        ),
      }),
    ],
    [],
  );

  const table = useReactTable({
    data: filtered,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: table.getRowModel().rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 12,
  });

  const exportCsv = () => {
    const blob = new Blob([toCsv(filtered)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "frostglass-requests.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <AppShell>
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl">Requests</h1>
          <p className="text-sm text-muted">Who is sending what, and what happened to it.</p>
        </div>
        <Button variant="default" size="sm" onClick={exportCsv} disabled={filtered.length === 0}>
          Export CSV
        </Button>
      </header>

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="w-64">
          <Input
            placeholder="Filter by user, team, model, id"
            value={text}
            onChange={(event) => setText(event.target.value)}
            aria-label="Free text filter"
          />
        </div>
        <div className="inline-flex overflow-hidden rounded border border-hairline">
          {OUTCOME_FILTERS.map((value) => (
            <button
              key={value}
              onClick={() => setOutcome(value)}
              aria-pressed={outcome === value}
              className={
                outcome === value
                  ? "bg-hairline px-3 py-1 text-sm text-text"
                  : "px-3 py-1 text-sm text-muted hover:text-text"
              }
            >
              {value}
            </button>
          ))}
        </div>
        <span className="text-sm text-muted">{filtered.length} shown</span>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={() => setOutcome((prev) => prev)} />
      ) : rows === null ? (
        <LoadingState label="Loading requests" />
      ) : filtered.length === 0 ? (
        <EmptyState title="No matching requests" hint="Widen the filter or send traffic through the gateway." />
      ) : (
        <div className="rounded border border-hairline">
          <div className="grid grid-cols-[1.6fr_1fr_1fr_1.2fr_1fr_1.1fr_0.8fr_0.8fr_0.9fr] gap-0 border-b border-hairline bg-raised px-3 py-2 text-sm text-muted">
            {table.getHeaderGroups()[0].headers.map((header) => (
              <div key={header.id}>
                {flexRender(header.column.columnDef.header, header.getContext())}
              </div>
            ))}
          </div>
          <div ref={parentRef} className="max-h-[60vh] overflow-auto">
            <div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = table.getRowModel().rows[virtualRow.index];
                return (
                  <button
                    key={row.id}
                    onClick={() => setSelected(row.original)}
                    className="absolute left-0 grid w-full grid-cols-[1.6fr_1fr_1fr_1.2fr_1fr_1.1fr_0.8fr_0.8fr_0.9fr] items-center gap-0 border-b border-hairline px-3 text-left text-sm hover:bg-raised"
                    style={{ height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <div key={cell.id} className="truncate">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </div>
                    ))}
                  </button>
                );
              })}
            </div>
          </div>
          {nextCursor ? (
            <div className="border-t border-hairline p-3">
              <Button variant="ghost" size="sm" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? "Loading..." : "Load more"}
              </Button>
            </div>
          ) : null}
        </div>
      )}

      <RequestDrawer request={selected} onClose={() => setSelected(null)} />
    </AppShell>
  );
}

function RequestDrawer({
  request,
  onClose,
}: {
  request: RequestView | null;
  onClose: () => void;
}) {
  const { session } = useSession();
  const [trace, setTrace] = useState<FindingView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!request) return;
    let active = true;
    setTrace(null);
    setError(null);
    api
      .trace(session.token, request.id)
      .then((data) => active && setTrace(data.trace))
      .catch((err: unknown) => {
        if (!active) return;
        // A viewer lacks READ_TRACE; show a permission-aware message, not a crash.
        setError(
          err instanceof ApiError && err.status === 403
            ? "Your role cannot read the decision trace."
            : err instanceof ApiError
              ? err.message
              : "Could not load the trace.",
        );
      });
    return () => {
      active = false;
    };
  }, [request, session.token]);

  return (
    <Drawer open={request !== null} onOpenChange={(open) => !open && onClose()} title="Request detail">
      {request ? (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="Request id" mono value={request.id} />
            <Field label="Outcome" value={request.action} />
            <Field label="User" value={request.user} />
            <Field label="Team" value={request.team} />
            <Field label="Model" mono value={request.model} />
            <Field label="Provider" value={request.provider} />
            <Field label="Policy version" mono value={String(request.policy_version)} />
            <Field label="Cost" mono value={formatCents(request.cost_cents)} />
          </div>

          {request.blocked_reason ? (
            <div className="rounded border border-blocked/40 bg-blocked/10 p-3 text-sm">
              <span className="text-blocked">Blocked:</span> {request.blocked_reason}
            </div>
          ) : null}

          <div>
            <h3 className="mb-2 text-sm text-muted">Decision trace</h3>
            {error ? (
              <ErrorState message={error} />
            ) : trace === null ? (
              <LoadingState label="Loading trace" />
            ) : trace.length === 0 ? (
              <p className="text-sm text-muted">No findings on this request.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {trace.map((finding, index) => (
                  <li key={index} className="rounded border border-hairline p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span>{finding.entity_type}</span>
                      <OutcomeChip outcome={(finding.action as never) ?? "masked"} />
                    </div>
                    <p className="mt-1 text-muted">{finding.reason}</p>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                      <span>detector <span className="font-mono">{finding.detector}</span></span>
                      <span>confidence <span className="font-mono">{finding.confidence.toFixed(2)}</span></span>
                      <span>span <span className="font-mono">[{finding.span[0]}, {finding.span[1]}]</span></span>
                      {finding.matched_rule_id ? (
                        <span>rule <span className="font-mono">{finding.matched_rule_id}</span></span>
                      ) : null}
                      {finding.false_positive_reported ? <span>false positive reported</span> : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <p className="text-xs text-muted">
            Content not captured (by policy). Frostglass stores metadata and the decision trace only,
            never the original text.
          </p>
        </div>
      ) : null}
    </Drawer>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-muted">{label}</p>
      <p className={mono ? "font-mono" : undefined}>{value}</p>
    </div>
  );
}
