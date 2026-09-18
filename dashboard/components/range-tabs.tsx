"use client";

import { useState } from "react";

// A range selector used by the stats-backed pages. Values map to the range
// tokens the Admin API accepts (_range_days): 24h, 7d, 30d.
const RANGES = [
  { value: "24h", label: "24h" },
  { value: "7d", label: "7d" },
  { value: "30d", label: "30d" },
];

export function RangeTabs({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="inline-flex overflow-hidden rounded border border-hairline">
      {RANGES.map((range) => (
        <button
          key={range.value}
          onClick={() => onChange(range.value)}
          aria-pressed={value === range.value}
          className={
            value === range.value
              ? "bg-hairline px-3 py-1 text-sm text-text"
              : "px-3 py-1 text-sm text-muted hover:text-text"
          }
        >
          {range.label}
        </button>
      ))}
    </div>
  );
}

export function useRange(initial = "7d") {
  return useState(initial);
}
