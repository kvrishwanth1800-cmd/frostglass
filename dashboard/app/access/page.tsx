"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";
import { can } from "@/lib/rbac";
import type { IssuedKey, KeyRow, TeamView, UserRow } from "@/lib/types";
import { formatCents, formatTs } from "@/lib/utils";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { ConfirmDialog } from "@/components/ui/dialog";
import { LoadingState, ErrorState, PermissionState } from "@/components/states";

export default function AccessPage() {
  const { session } = useSession();
  const mayRead = can(session.role, "read_access");
  const mayWrite = can(session.role, "write_access");
  const [users, setUsers] = useState<UserRow[] | null>(null);
  const [teams, setTeams] = useState<TeamView[] | null>(null);
  const [keys, setKeys] = useState<KeyRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setUsers(null);
    setTeams(null);
    setKeys(null);
    Promise.all([api.users(session.token), api.teams(session.token), api.keys(session.token)])
      .then(([userList, teamList, keyList]) => {
        setUsers(userList.items);
        setTeams(teamList.items);
        setKeys(keyList.items);
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : "Could not load access data."),
      );
  };

  useEffect(load, [session.token]);

  if (!mayRead) {
    return (
      <AppShell>
        <h1 className="mb-4 text-xl">Access and budgets</h1>
        <PermissionState action="view access settings" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <header className="mb-4">
        <h1 className="text-xl">Access and budgets</h1>
        <p className="text-sm text-muted">Who can use the gateway, and how much.</p>
      </header>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : users === null || teams === null || keys === null ? (
        <LoadingState label="Loading access data" />
      ) : (
        <div className="flex flex-col gap-8">
          <section>
            <h2 className="mb-2 text-lg">Teams</h2>
            <div className="flex flex-col gap-3">
              {teams.map((team) => (
                <TeamCard key={team.id} team={team} mayWrite={mayWrite} onSaved={load} />
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-2 text-lg">Users</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted">
                  <th className="border-b border-hairline py-2">Name</th>
                  <th className="border-b border-hairline py-2">Email</th>
                  <th className="border-b border-hairline py-2">Role</th>
                  <th className="border-b border-hairline py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="border-b border-hairline py-2">{user.name}</td>
                    <td className="border-b border-hairline py-2 font-mono text-muted">{user.email}</td>
                    <td className="border-b border-hairline py-2">{user.role}</td>
                    <td className="border-b border-hairline py-2 text-muted">
                      {user.disabled_at ? "Disabled" : "Active"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-lg">API keys</h2>
              {mayWrite ? <IssueKey teams={teams} onIssued={load} /> : null}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted">
                  <th className="border-b border-hairline py-2">Name</th>
                  <th className="border-b border-hairline py-2">Team</th>
                  <th className="border-b border-hairline py-2">Prefix</th>
                  <th className="border-b border-hairline py-2">Created</th>
                  <th className="border-b border-hairline py-2">Status</th>
                  <th className="border-b border-hairline py-2" />
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key.id}>
                    <td className="border-b border-hairline py-2">{key.name}</td>
                    <td className="border-b border-hairline py-2">{key.team}</td>
                    <td className="border-b border-hairline py-2 font-mono text-muted">{key.key_prefix}...</td>
                    <td className="border-b border-hairline py-2 font-mono text-muted">{formatTs(key.created_at)}</td>
                    <td className="border-b border-hairline py-2 text-muted">
                      {key.revoked_at ? "Revoked" : "Active"}
                    </td>
                    <td className="border-b border-hairline py-2 text-right">
                      {mayWrite && !key.revoked_at ? (
                        <RevokeKey keyId={key.id} keyName={key.name} onRevoked={load} />
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </AppShell>
  );
}

function TeamCard({
  team,
  mayWrite,
  onSaved,
}: {
  team: TeamView;
  mayWrite: boolean;
  onSaved: () => void;
}) {
  const { session } = useSession();
  const [budget, setBudget] = useState(String(team.monthly_budget_cents));
  const [rate, setRate] = useState(String(team.rate_limit_rpm));
  const [models, setModels] = useState(team.allowed_models.join(", "));
  const [shadow, setShadow] = useState(team.shadow_mode);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.updateTeam(session.token, team.id, {
        monthly_budget_cents: Number(budget),
        rate_limit_rpm: Number(rate),
        allowed_models: models
          .split(",")
          .map((model) => model.trim())
          .filter(Boolean),
        shadow_mode: shadow,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save team.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded border border-hairline bg-raised p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-base">{team.name}</span>
        <label className="flex items-center gap-2 text-sm text-muted">
          Shadow mode
          <Switch checked={shadow} onCheckedChange={setShadow} disabled={!mayWrite} aria-label={`Shadow mode for ${team.name}`} />
        </label>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="text-sm text-muted">
          Monthly budget (cents)
          <Input
            className="mt-1"
            value={budget}
            onChange={(event) => setBudget(event.target.value)}
            disabled={!mayWrite}
            inputMode="numeric"
          />
          <span className="mt-1 block text-xs">{formatCents(Number(budget))}/mo</span>
        </label>
        <label className="text-sm text-muted">
          Rate limit (rpm)
          <Input
            className="mt-1"
            value={rate}
            onChange={(event) => setRate(event.target.value)}
            disabled={!mayWrite}
            inputMode="numeric"
          />
        </label>
        <label className="text-sm text-muted">
          Allowed models (comma separated, empty = all)
          <Input
            className="mt-1"
            value={models}
            onChange={(event) => setModels(event.target.value)}
            disabled={!mayWrite}
          />
        </label>
      </div>
      {error ? <p className="mt-2 text-sm text-blocked">{error}</p> : null}
      {mayWrite ? (
        <div className="mt-3">
          <Button variant="primary" size="sm" onClick={save} disabled={busy}>
            {busy ? "Saving..." : "Save team"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function IssueKey({ teams, onIssued }: { teams: TeamView[]; onIssued: () => void }) {
  const { session } = useSession();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [team, setTeam] = useState(teams[0]?.name ?? "");
  const [issued, setIssued] = useState<IssuedKey | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      setIssued(await api.createKey(session.token, team, name));
      onIssued();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not issue key.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button variant="default" size="sm" onClick={() => setOpen(true)}>
        Issue key
      </Button>
      <ConfirmDialog open={open} onOpenChange={(next) => { setOpen(next); if (!next) setIssued(null); }} title="Issue API key">
        {issued ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted">
              Copy this key now. It is shown once and cannot be retrieved again.
            </p>
            <code className="break-all rounded border border-hairline bg-canvas p-3 font-mono text-sm">
              {issued.key}
            </code>
            <Button variant="primary" onClick={() => { setOpen(false); setIssued(null); }}>
              Done
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <label className="text-sm text-muted">
              Key name
              <Input className="mt-1" value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="text-sm text-muted">
              Team
              <select
                className="mt-1 w-full rounded border border-hairline bg-canvas px-2 py-2 text-sm text-text"
                value={team}
                onChange={(event) => setTeam(event.target.value)}
              >
                {teams.map((item) => (
                  <option key={item.id} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            {error ? <p className="text-sm text-blocked">{error}</p> : null}
            <Button variant="primary" onClick={create} disabled={busy || !name.trim()}>
              {busy ? "Issuing..." : "Issue key"}
            </Button>
          </div>
        )}
      </ConfirmDialog>
    </>
  );
}

function RevokeKey({ keyId, keyName, onRevoked }: { keyId: string; keyName: string; onRevoked: () => void }) {
  const { session } = useSession();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const revoke = async () => {
    setBusy(true);
    try {
      await api.revokeKey(session.token, keyId);
      onRevoked();
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button variant="destructive" size="sm" onClick={() => setOpen(true)}>
        Revoke
      </Button>
      <ConfirmDialog open={open} onOpenChange={setOpen} title="Revoke API key">
        <p className="mb-4 text-sm text-muted">
          Revoking <span className="text-text">{keyName}</span> immediately stops any traffic using it.
          This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={revoke} disabled={busy}>
            {busy ? "Revoking..." : "Revoke key"}
          </Button>
        </div>
      </ConfirmDialog>
    </>
  );
}
