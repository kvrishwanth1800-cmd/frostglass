import { cn } from "@/lib/utils";
import type { Outcome } from "@/lib/types";

// THE single source of outcome colour in the interface (H.6.1: "colour means
// policy outcome and nothing else"). Every request row, ledger tick, and trace
// entry renders its outcome through this component, so there is exactly one
// place where a signal colour is attached to meaning. AC-M6-05 audits that no
// colour appears outside these tokens.
const OUTCOME_STYLE: Record<Outcome, { dot: string; text: string; label: string }> = {
  blocked: { dot: "bg-blocked", text: "text-blocked", label: "Blocked" },
  masked: { dot: "bg-masked", text: "text-masked", label: "Masked" },
  shadow: { dot: "bg-shadow", text: "text-shadow", label: "Shadow" },
  allowed: { dot: "bg-muted", text: "text-muted", label: "Allowed" },
};

export function OutcomeChip({ outcome }: { outcome: Outcome }) {
  const style = OUTCOME_STYLE[outcome] ?? OUTCOME_STYLE.allowed;
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm", style.text)}>
      <span className={cn("h-2 w-2 rounded-full", style.dot)} aria-hidden="true" />
      {style.label}
    </span>
  );
}

export function outcomeDotClass(outcome: string): string {
  return (OUTCOME_STYLE[outcome as Outcome] ?? OUTCOME_STYLE.allowed).dot;
}
