"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";
import { can } from "@/lib/rbac";
import type { SettingsView } from "@/lib/types";
import { formatTs } from "@/lib/utils";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { ConfirmDialog } from "@/components/ui/dialog";
import { LoadingState, ErrorState, PermissionState } from "@/components/states";

export default function SettingsPage() {
  const { session } = useSession();
  const mayRead = can(session.role, "read_settings");
  const mayWrite = can(session.role, "write_settings");
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setSettings(null);
    api
      .settings(session.token)
      .then(setSettings)
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : "Could not load settings."),
      );
  };

  useEffect(load, [session.token]);

  if (!mayRead) {
    return (
      <AppShell>
        <h1 className="mb-4 text-xl">Settings</h1>
        <PermissionState action="view settings" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <header className="mb-4">
        <h1 className="text-xl">Settings</h1>
        <p className="text-sm text-muted">Provider keys, retention, sign-in, and the masking vault.</p>
      </header>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : settings === null ? (
        <LoadingState label="Loading settings" />
      ) : (
        <div className="flex max-w-3xl flex-col gap-8">
          <ProviderKeys settings={settings} mayWrite={mayWrite} onSaved={load} />
          <Retention settings={settings} mayWrite={mayWrite} onSaved={load} />
          <ContentCapture settings={settings} mayWrite={mayWrite} onSaved={load} />
          <Sso settings={settings} mayWrite={mayWrite} onSaved={load} />
          <Vault settings={settings} mayWrite={mayWrite} onSaved={load} />
        </div>
      )}
    </AppShell>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="rounded border border-hairline bg-raised p-4">
      <h2 className="text-lg">{title}</h2>
      {hint ? <p className="mb-3 mt-1 text-sm text-muted">{hint}</p> : <div className="mb-3" />}
      {children}
    </section>
  );
}

function ProviderKeys({
  settings,
  mayWrite,
  onSaved,
}: {
  settings: SettingsView;
  mayWrite: boolean;
  onSaved: () => void;
}) {
  const { session } = useSession();
  const [provider, setProvider] = useState("openai");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.setProviderCredential(session.token, provider, secret);
      setSecret("");
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save provider key.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section
      title="Provider API keys"
      hint="Keys are write-only. Once saved, only the last four digits are ever shown."
    >
      <ul className="mb-3 flex flex-col gap-1 text-sm">
        {settings.provider_credentials.length === 0 ? (
          <li className="text-muted">No provider keys stored yet.</li>
        ) : (
          settings.provider_credentials.map((cred) => (
            <li key={cred.provider} className="flex justify-between">
              <span>{cred.provider}</span>
              <span className="font-mono text-muted">****{cred.key_last4} - updated {formatTs(cred.updated_at)}</span>
            </li>
          ))
        )}
      </ul>
      {mayWrite ? (
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm text-muted">
            Provider
            <Input className="mt-1 w-40" value={provider} onChange={(event) => setProvider(event.target.value)} />
          </label>
          <label className="flex-1 text-sm text-muted">
            Secret
            <Input
              className="mt-1"
              type="password"
              value={secret}
              onChange={(event) => setSecret(event.target.value)}
              placeholder="sk-..."
            />
          </label>
          {error ? <p className="w-full text-sm text-blocked">{error}</p> : null}
          <Button variant="primary" onClick={save} disabled={busy || !secret.trim()}>
            {busy ? "Saving..." : "Save key"}
          </Button>
        </div>
      ) : null}
    </Section>
  );
}

function Retention({
  settings,
  mayWrite,
  onSaved,
}: {
  settings: SettingsView;
  mayWrite: boolean;
  onSaved: () => void;
}) {
  const { session } = useSession();
  const [audit, setAudit] = useState(String(settings.audit_retention_days));
  const [capture, setCapture] = useState(String(settings.capture_retention_days));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.updateSettings(session.token, {
        audit_retention_days: Number(audit),
        capture_retention_days: Number(capture),
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save retention.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section title="Retention" hint="How long audit rows and any masked captures are kept.">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-muted">
          Audit retention (days)
          <Input className="mt-1 w-40" value={audit} onChange={(event) => setAudit(event.target.value)} disabled={!mayWrite} inputMode="numeric" />
        </label>
        <label className="text-sm text-muted">
          Capture retention (days)
          <Input className="mt-1 w-40" value={capture} onChange={(event) => setCapture(event.target.value)} disabled={!mayWrite} inputMode="numeric" />
        </label>
        {error ? <p className="w-full text-sm text-blocked">{error}</p> : null}
        {mayWrite ? (
          <Button variant="primary" onClick={save} disabled={busy}>
            {busy ? "Saving..." : "Save retention"}
          </Button>
        ) : null}
      </div>
    </Section>
  );
}

function ContentCapture({
  settings,
  mayWrite,
  onSaved,
}: {
  settings: SettingsView;
  mayWrite: boolean;
  onSaved: () => void;
}) {
  const { session } = useSession();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const setEnabled = async (enabled: boolean) => {
    setBusy(true);
    try {
      await api.updateSettings(session.token, { content_capture_enabled: enabled });
      onSaved();
    } finally {
      setBusy(false);
      setConfirmOpen(false);
    }
  };

  return (
    <Section
      title="Content capture"
      hint="When on, the masked prompt is stored so you can inspect exactly what left the network. The original secret is never stored."
    >
      <label className="flex items-center gap-2 text-sm">
        <Switch
          checked={settings.content_capture_enabled}
          disabled={!mayWrite || busy}
          onCheckedChange={(next) => {
            if (next) setConfirmOpen(true);
            else setEnabled(false);
          }}
          aria-label="Content capture"
        />
        {settings.content_capture_enabled ? "Enabled" : "Disabled"}
      </label>
      <ConfirmDialog open={confirmOpen} onOpenChange={setConfirmOpen} title="Enable content capture?">
        <p className="mb-4 text-sm text-muted">
          This stores the masked prompt text for every request until capture retention expires. Only
          enable this if your compliance policy allows retaining masked content.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => setEnabled(true)} disabled={busy}>
            {busy ? "Enabling..." : "Enable capture"}
          </Button>
        </div>
      </ConfirmDialog>
    </Section>
  );
}

function Sso({
  settings,
  mayWrite,
  onSaved,
}: {
  settings: SettingsView;
  mayWrite: boolean;
  onSaved: () => void;
}) {
  const { session } = useSession();
  const [enabled, setEnabled] = useState(settings.sso_enabled);
  const [providerName, setProviderName] = useState(settings.sso_provider ?? "");
  const [clientId, setClientId] = useState(settings.sso_client_id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.updateSettings(session.token, {
        sso_enabled: enabled,
        sso_provider: providerName || null,
        sso_client_id: clientId || null,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save SSO settings.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section title="Single sign-on (OIDC)" hint="Let users sign in through your identity provider.">
      <label className="mb-3 flex items-center gap-2 text-sm">
        <Switch checked={enabled} onCheckedChange={setEnabled} disabled={!mayWrite} aria-label="SSO enabled" />
        {enabled ? "Enabled" : "Disabled"}
      </label>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-muted">
          Provider
          <Input className="mt-1 w-40" value={providerName} onChange={(event) => setProviderName(event.target.value)} disabled={!mayWrite} placeholder="okta" />
        </label>
        <label className="flex-1 text-sm text-muted">
          Client ID
          <Input className="mt-1" value={clientId} onChange={(event) => setClientId(event.target.value)} disabled={!mayWrite} />
        </label>
        {error ? <p className="w-full text-sm text-blocked">{error}</p> : null}
        {mayWrite ? (
          <Button variant="primary" onClick={save} disabled={busy}>
            {busy ? "Saving..." : "Save SSO"}
          </Button>
        ) : null}
      </div>
    </Section>
  );
}

function Vault({
  settings,
  mayWrite,
  onSaved,
}: {
  settings: SettingsView;
  mayWrite: boolean;
  onSaved: () => void;
}) {
  const { session } = useSession();
  const [busy, setBusy] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const rotate = async () => {
    setBusy(true);
    try {
      await api.rotateVaultKey(session.token);
      onSaved();
      setConfirmOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section
      title="Masking vault"
      hint="The vault key encrypts pseudonym mappings. Rotating it re-seals future mappings under a new key."
    >
      <p className="mb-3 text-sm">
        Last rotated:{" "}
        <span className="font-mono text-muted">
          {settings.vault_key_rotated_at ? formatTs(settings.vault_key_rotated_at) : "never"}
        </span>
      </p>
      {mayWrite ? (
        <>
          <Button variant="default" onClick={() => setConfirmOpen(true)}>
            Rotate vault key
          </Button>
          <ConfirmDialog open={confirmOpen} onOpenChange={setConfirmOpen} title="Rotate vault key?">
            <p className="mb-4 text-sm text-muted">
              New pseudonym mappings will be sealed under a new key. Existing mappings remain readable.
              This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={rotate} disabled={busy}>
                {busy ? "Rotating..." : "Rotate key"}
              </Button>
            </div>
          </ConfirmDialog>
        </>
      ) : null}
    </Section>
  );
}
