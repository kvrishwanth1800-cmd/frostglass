"use client";

import { useEffect, useMemo, useState } from "react";
import type { RequestView } from "@/lib/types";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { outcomeDotClass } from "@/components/ui/outcome";
import { LoadingState, ErrorState, EmptyState } from "@/components/states";
import { ApiError } from "@/lib/api";

// The live outcome ledger: the last ~200 requests as a dense horizontal strip
// of ticks, each coloured by outcome (H.6.1 "the Overview hero"). It shows, in
// one glance, that traffic is flowing and what is happening to it. Colour here
// comes only from the outcome signal tokens.
export function OutcomeLedger() {
  const { session } = useSession();
  const [items, setItems] = useState<RequestView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setItems(null);
    setError(null);
    api
      .requests(session.token, { limit: 100 })
      .then((page) => {
        if (active) setItems(page.items.slice(0, 200));
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load the ledger.");
      });
    return () => {
      active = false;
    };
  }, [session.token]);

  const counts = useMemo(() => {
    const tally: Record<string, number> = {};
    for (const item of items ?? []) tally[item.action] = (tally[item.action] ?? 0) + 1;
    return tally;
  }, [items]);

  return (
    <section className="rounded border border-hairline bg-raised p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-lg">Live outcome ledger</h2>
        <span className="text-sm text-muted">last {items?.length ?? 0} requests</span>
      </div>
      {error ? (
        <ErrorState message={error} />
      ) : items === null ? (
        <LoadingState label="Reading the stream" />
      ) : items.length === 0 ? (
        <EmptyState title="No requests yet" hint="Send a request through the gateway to see it here." />
      ) : (
        <>
          <div className="flex flex-wrap gap-[3px]" role="img" aria-label="Recent request outcomes">
            {items.map((item) => (
              <span
                key={item.id}
                title={`${item.action} - ${item.user} - ${item.model}`}
                className={`h-6 w-1.5 rounded-sm ${outcomeDotClass(item.action)}`}
              />
            ))}
          </div>
          <div className="mt-3 flex gap-4 text-sm text-muted">
            {["blocked", "masked", "shadow", "allowed"].map((outcome) => (
              <span key={outcome} className="flex items-center gap-1.5">
                <span className={`h-2 w-2 rounded-full ${outcomeDotClass(outcome)}`} />
                {outcome} {counts[outcome] ?? 0}
              </span>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
