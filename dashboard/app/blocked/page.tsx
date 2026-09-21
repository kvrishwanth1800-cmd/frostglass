"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";
import { can } from "@/lib/rbac";
import type { FalsePositiveRate, FindingView, RequestView } from "@/lib/types";
import { formatPct, formatTs } from "@/lib/utils";
import { AppShell } from "@/components/app-shell";
import { RangeTabs } from "@/components/range-tabs";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/dialog";
import { LoadingState, ErrorState, EmptyState } from "@/components/states";

export default function BlockedPage() {
  const { session } = useSession();
  const [range, setRange] = useState("7d");
  const [rows, setRows] = useState<RequestView[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fpRate, setFpRate] = useState<FalsePositiveRate | null>(null);
  const [selected, setSelected] = useState<RequestView | null>(null);

  const load = useCallback(() => {
    let active = true;
    setRows(null);
    setError(null);
    api
      .requests(session.token, { action: "blocked", limit: 100 })
      .then((page) => active && setRows(page.items))
      .catch((err: unknown) =>
        active && setError(err instanceof ApiError ? err.message : "Could not load blocked feed."),
      );
    api
      .falsePositives(session.token, range)
      .then((data) => active && setFpRate(data))
      .catch(() => active && setFpRate(null));
    return () => {
      active = false;
    };
  }, [session.token, range]);

  useEffect(() => load(), [load]);

  return (
    <AppShell>
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl">Blocked and flagged</h1>
          <p className="text-sm text-muted">What was stopped, and why.</p>
        </div>
        <RangeTabs value={range} onChange={setRange} />
      </header>

      <div className="mb-4 rounded border border-hairline bg-raised p-4">
        <h3 className="text-sm text-muted">False-positive rate</h3>
        {fpRate === null ? (
          <p className="mt-1 text-sm text-muted">Not available.</p>
        ) : (
          <p className="mt-1 text-xl">
            {formatPct(fpRate.rate)}{" "}
            <span className="text-sm text-muted">
              ({fpRate.reported} reported of {fpRate.total} findings)
            </span>
          </p>
        )}
        <p className="mt-1 text-xs text-muted">
          A rising rate is the signal to loosen a rule or raise its confidence floor.
        </p>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : rows === null ? (
        <LoadingState label="Loading blocked requests" />
      ) : rows.length === 0 ? (
        <EmptyState title="Nothing has been blocked" hint="Blocked requests will appear here newest first." />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((row) => (
            <li key={row.id} className="rounded border border-blocked/40 bg-blocked/5 p-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm">
                    <span className="text-blocked">Blocked:</span>{" "}
                    {row.blocked_reason ?? "Policy blocked this request."}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    <span className="font-mono">{formatTs(row.ts)}</span> - {row.user} - {row.team} -{" "}
                    <span className="font-mono">{row.model}</span>
                  </p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setSelected(row)}>
                  View trace
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <BlockedDrawer request={selected} onClose={() => setSelected(null)} onChanged={load} />
    </AppShell>
  );
}

function BlockedDrawer({
  request,
  onClose,
  onChanged,
}: {
  request: RequestView | null;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { session } = useSession();
  const [trace, setTrace] = useState<FindingView[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyFindingId, setBusyFindingId] = useState<string | null>(null);
  const mayReport = can(session.role, "report_false_positive");

  useEffect(() => {
    if (!request) return;
    let active = true;
    setTrace(null);
    setError(null);
    api
      .trace(session.token, request.id)
      .then((data) => active && setTrace(data.trace))
      .catch((err: unknown) =>
        active &&
        setError(
          err instanceof ApiError && err.status === 403
            ? "Your role cannot read the decision trace."
            : err instanceof ApiError
              ? err.message
              : "Could not load the trace.",
        ),
      );
    return () => {
      active = false;
    };
  }, [request, session.token]);

  const reportFalsePositive = async (findingId: string) => {
    setBusyFindingId(findingId);
    try {
      await api.reportFalsePositive(session.token, findingId);
      setTrace((current) =>
        current
          ? current.map((finding) =>
              finding.id === findingId ? { ...finding, false_positive_reported: true } : finding,
            )
          : current,
      );
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not report false positive.");
    } finally {
      setBusyFindingId(null);
    }
  };

  return (
    <Drawer open={request !== null} onOpenChange={(open) => !open && onClose()} title="Blocked request">
      {request ? (
        <div className="flex flex-col gap-4">
          <div className="rounded border border-blocked/40 bg-blocked/10 p-3 text-sm">
            <span className="text-blocked">Blocked:</span>{" "}
            {request.blocked_reason ?? "Policy blocked this request."}
          </div>
          <p className="text-xs text-muted">
            The offending value is never shown - only its type, position, and hash appear in the
            trace below.
          </p>

          {error ? (
            <ErrorState message={error} />
          ) : trace === null ? (
            <LoadingState label="Loading trace" />
          ) : trace.length === 0 ? (
            <p className="text-sm text-muted">No findings recorded.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {trace.map((finding) => (
                <li key={finding.id} className="rounded border border-hairline p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span>{finding.entity_type}</span>
                    {finding.false_positive_reported ? (
                      <span className="text-xs text-muted">false positive reported</span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-muted">{finding.reason}</p>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                    <span>detector <span className="font-mono">{finding.detector}</span></span>
                    <span>confidence <span className="font-mono">{finding.confidence.toFixed(2)}</span></span>
                    {finding.matched_rule_id ? (
                      <span>rule <span className="font-mono">{finding.matched_rule_id}</span></span>
                    ) : null}
                  </div>
                  {mayReport && !finding.false_positive_reported ? (
                    <div className="mt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => reportFalsePositive(finding.id)}
                        disabled={busyFindingId === finding.id}
                      >
                        {busyFindingId === finding.id ? "Reporting..." : "Mark false positive"}
                      </Button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}

          {mayReport ? null : (
            <p className="text-xs text-muted">Your role cannot report false positives.</p>
          )}
        </div>
      ) : null}
    </Drawer>
  );
}
