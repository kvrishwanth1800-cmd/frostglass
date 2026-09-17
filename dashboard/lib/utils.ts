import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format integer cents as USD. Machine value -> render in mono at call site. */
export function formatCents(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return "-";
  return `$${(cents / 100).toFixed(2)}`;
}

export function formatPct(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}%`;
}

export function formatTs(ts: string): string {
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return ts;
  return date.toISOString().replace("T", " ").slice(0, 19);
}
