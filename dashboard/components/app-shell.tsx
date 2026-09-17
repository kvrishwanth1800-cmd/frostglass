"use client";

import {
  Activity,
  KeyRound,
  ListFilter,
  ShieldAlert,
  SlidersHorizontal,
  Settings as SettingsIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { SEEDED_SESSIONS, useSession } from "@/lib/session";
import { cn } from "@/lib/utils";

// Persistent left-rail navigation (H.6.1). Pages 5 and 6 (detectors,
// suggestions) are M7; they are intentionally absent here.
const NAV = [
  { href: "/", label: "Overview", icon: Activity },
  { href: "/requests", label: "Requests", icon: ListFilter },
  { href: "/blocked", label: "Blocked and flagged", icon: ShieldAlert },
  { href: "/policy", label: "Policy editor", icon: SlidersHorizontal },
  { href: "/access", label: "Access and budgets", icon: KeyRound },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  useEffect(() => {
    const stored = (window.localStorage.getItem("fg-theme") as "dark" | "light") ?? "dark";
    setTheme(stored);
    document.documentElement.setAttribute("data-theme", stored);
  }, []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    window.localStorage.setItem("fg-theme", next);
  };
  return (
    <button
      onClick={toggle}
      className="w-full rounded border border-hairline px-3 py-2 text-left text-sm text-muted hover:text-text"
    >
      Theme: {theme === "dark" ? "Dark" : "Light"}
    </button>
  );
}

function RoleSwitcher() {
  const { session, setSession } = useSession();
  return (
    <label className="block text-sm text-muted">
      Signed in as
      <select
        aria-label="Signed in as"
        className="mt-1 w-full rounded border border-hairline bg-canvas px-2 py-2 text-sm text-text"
        value={session.token}
        onChange={(event) => {
          const next = SEEDED_SESSIONS.find((item) => item.token === event.target.value);
          if (next) setSession(next);
        }}
      >
        {SEEDED_SESSIONS.map((item) => (
          <option key={item.token} value={item.token}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen">
      <nav className="flex w-60 shrink-0 flex-col gap-1 border-r border-hairline bg-raised p-4">
        <div className="mb-4 px-2">
          <span className="text-lg font-semibold">Frostglass</span>
          <p className="text-xs text-muted">Prompt boundary inspector</p>
        </div>
        {NAV.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2 rounded px-2 py-2 text-sm",
                active ? "bg-hairline text-text" : "text-muted hover:text-text",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
        <div className="mt-auto flex flex-col gap-3 pt-4">
          <RoleSwitcher />
          <ThemeToggle />
        </div>
      </nav>
      <main className="min-w-0 flex-1 p-6">{children}</main>
    </div>
  );
}
