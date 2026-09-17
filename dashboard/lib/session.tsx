"use client";

// Local session (H.6 allows "OIDC or local sessions"). The dashboard holds an
// opaque Admin API session token and the role it resolves to. In this build
// the tokens are the seeded per-role sessions; production swaps this provider
// for an OIDC callback that yields the same shape.

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { Role } from "./rbac";

export interface Session {
  token: string;
  role: Role;
  label: string;
}

// Seeded sessions from frostglass/main.py _SESSION_TOKENS. The viewer is on a
// separate team, which is why team-scoped views differ by role.
export const SEEDED_SESSIONS: Session[] = [
  { token: "fg-admin-owner-token", role: "owner", label: "Owner" },
  { token: "fg-admin-admin-token", role: "admin", label: "Admin" },
  { token: "fg-admin-auditor-token", role: "auditor", label: "Auditor" },
  { token: "fg-admin-viewer-token", role: "viewer", label: "Viewer" },
];

interface SessionContextValue {
  session: Session;
  setSession: (session: Session) => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);
const STORAGE_KEY = "fg-session-token";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = useState<Session>(SEEDED_SESSIONS[0]);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const match = SEEDED_SESSIONS.find((item) => item.token === stored);
      if (match) setSessionState(match);
    }
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      setSession: (next) => {
        window.localStorage.setItem(STORAGE_KEY, next.token);
        setSessionState(next);
      },
    }),
    [session],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === null) throw new Error("useSession must be used within SessionProvider");
  return context;
}
