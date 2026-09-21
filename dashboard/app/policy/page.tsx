"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";
import { can } from "@/lib/rbac";
import type {
  DetectionEstimates,
  PolicyTestResult,
  PolicyVersions,
  RuleSetView,
  TeamView,
} from "@/lib/types";
import {
  ACTIONS,
  ENTITY_GROUPS,
  buildPolicyYaml,
  matrixFromRuleset,
  type MatrixRow,
  type PolicyAction,
} from "@/lib/policy";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { ConfirmDialog } from "@/components/ui/dialog";
import { LoadingState, ErrorState, PermissionState } from "@/components/states";

export default function PolicyPage() {
  const { session } = useSession();
  const mayWrite = can(session.role, "write_policy");
  const [ruleset, setRuleset] = useState<RuleSetView | null>(null);
  const [versions, setVersions] = useState<PolicyVersions | null>(null);
  const [estimates, setEstimates] = useState<DetectionEstimates | null>(null);
  const [teams, setTeams] = useState<TeamView[]>([]);
  const [rows, setRows] = useState<MatrixRow[]>([]);
  const [scopeTeams, setScopeTeams] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    Promise.all([
      api.policies(session.token),
      api.policyVersions(session.token),
      api.detections(session.token, "7d").catch(() => null),
      api.teams(session.token).then((data) => data.items).catch(() => []),
    ])
      .then(([activeRuleset, versionList, detectionEstimates, teamList]) => {
        setRuleset(activeRuleset);
        setVersions(versionList);
        setEstimates(detectionEstimates);
        setTeams(teamList);
        setRows(matrixFromRuleset(activeRuleset));
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : "Could not load policy."),
      );
  };

  useEffect(load, [session.token]);

  const nextVersion = useMemo(() => {
    const highest = versions?.versions.reduce((max, item) => Math.max(max, item.version), 0) ?? 0;
    return highest + 1;
  }, [versions]);

  const yaml = useMemo(
    () =>
      ruleset
        ? buildPolicyYaml(rows, nextVersion, ruleset.default_action as PolicyAction, scopeTeams)
        : "",
    [ruleset, rows, nextVersion, scopeTeams],
  );

  const setRowAction = (entity_type: string, action: PolicyAction) =>
    setRows((prev) => prev.map((row) => (row.entity_type === entity_type ? { ...row, action } : row)));
  const setRowConfidence = (entity_type: string, min_confidence: number) =>
    setRows((prev) =>
      prev.map((row) => (row.entity_type === entity_type ? { ...row, min_confidence } : row)),
    );

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const created = await api.createPolicy(session.token, yaml);
      await api.activatePolicy(session.token, created.version);
      setConfirmOpen(false);
      load();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not save policy.");
    } finally {
      setSaving(false);
    }
  };

  if (error) {
    return (
      <AppShell>
        <h1 className="mb-4 text-xl">Policy editor</h1>
        <ErrorState message={error} onRetry={load} />
      </AppShell>
    );
  }
  if (ruleset === null) {
    return (
      <AppShell>
        <h1 className="mb-4 text-xl">Policy editor</h1>
        <LoadingState label="Loading policy" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl">Policy editor</h1>
          <p className="text-sm text-muted">
            Active version <span className="font-mono">{ruleset.version}</span>. Default action{" "}
            <span className="font-mono">{ruleset.default_action}</span>.
          </p>
        </div>
        {mayWrite ? (
          <Button variant="primary" onClick={() => setConfirmOpen(true)} data-testid="review-save">
            Review and save
          </Button>
        ) : null}
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="lg:col-span-2" aria-label="Policy matrix">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="border-b border-hairline px-2 py-2 text-left text-muted">Entity type</th>
                <th className="border-b border-hairline px-2 py-2 text-left text-muted">Action</th>
                <th className="border-b border-hairline px-2 py-2 text-left text-muted">
                  Confidence floor
                </th>
              </tr>
            </thead>
            <tbody>
              {ENTITY_GROUPS.map((group) => (
                <GroupRows
                  key={group.group}
                  group={group.group}
                  entityTypes={group.entity_types}
                  rows={rows}
                  estimates={estimates}
                  mayWrite={mayWrite}
                  onAction={setRowAction}
                  onConfidence={setRowConfidence}
                />
              ))}
            </tbody>
          </table>

          <ScopeSelector teams={teams} scopeTeams={scopeTeams} onChange={setScopeTeams} disabled={!mayWrite} />
        </section>

        <aside className="flex flex-col gap-4">
          <Sandbox />
          <VersionHistory
            versions={versions}
            mayWrite={mayWrite}
            yaml={yaml}
            onActivate={async (version) => {
              await api.activatePolicy(session.token, version);
              load();
            }}
          />
        </aside>
      </div>

      <ConfirmDialog open={confirmOpen} onOpenChange={setConfirmOpen} title="Review policy change">
        <p className="mb-2 text-sm text-muted">
          This creates version <span className="font-mono">{nextVersion}</span> and activates it. Review
          the generated policy before saving.
        </p>
        <pre className="max-h-72 overflow-auto rounded border border-hairline bg-canvas p-3 font-mono text-xs">
          {yaml}
        </pre>
        {saveError ? <p className="mt-2 text-sm text-blocked">{saveError}</p> : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={save} disabled={saving} data-testid="confirm-save">
            {saving ? "Saving..." : "Save policy"}
          </Button>
        </div>
      </ConfirmDialog>
    </AppShell>
  );
}

function GroupRows({
  group,
  entityTypes,
  rows,
  estimates,
  mayWrite,
  onAction,
  onConfidence,
}: {
  group: string;
  entityTypes: string[];
  rows: MatrixRow[];
  estimates: DetectionEstimates | null;
  mayWrite: boolean;
  onAction: (entity_type: string, action: PolicyAction) => void;
  onConfidence: (entity_type: string, value: number) => void;
}) {
  return (
    <>
      <tr>
        <td colSpan={3} className="px-2 pb-1 pt-4 text-xs uppercase tracking-wide text-muted">
          {group}
        </td>
      </tr>
      {entityTypes.map((entity_type) => {
        const row = rows.find((candidate) => candidate.entity_type === entity_type);
        if (!row) return null;
        const bucket = estimates?.by_entity_type[entity_type];
        const threshold = row.min_confidence.toFixed(1);
        const atConfidence = bucket?.at_confidence[threshold];
        return (
          <tr key={entity_type} className="align-top">
            <td className="border-b border-hairline px-2 py-3">{entity_type}</td>
            <td className="border-b border-hairline px-2 py-3">
              <RadioGroup
                className="flex flex-wrap gap-3"
                value={row.action}
                onValueChange={(value) => onAction(entity_type, value as PolicyAction)}
                aria-label={`Action for ${entity_type}`}
                disabled={!mayWrite}
              >
                {ACTIONS.map((action) => (
                  <label key={action} className="flex items-center gap-1.5 text-sm">
                    <RadioGroupItem value={action} aria-label={`${entity_type} ${action}`} />
                    {action}
                  </label>
                ))}
              </RadioGroup>
            </td>
            <td className="border-b border-hairline px-2 py-3">
              <div className="w-48">
                <Slider
                  min={0}
                  max={1}
                  step={0.1}
                  value={[row.min_confidence]}
                  onValueChange={([value]) => onConfidence(entity_type, value)}
                  aria-label={`Confidence floor for ${entity_type}`}
                  disabled={!mayWrite}
                />
                <p className="mt-1 text-xs text-muted">
                  at <span className="font-mono">{threshold}</span>
                  {atConfidence === undefined
                    ? " - no recent data"
                    : ` - matched ${atConfidence} times in the last 7 days`}
                </p>
              </div>
            </td>
          </tr>
        );
      })}
    </>
  );
}

function ScopeSelector({
  teams,
  scopeTeams,
  onChange,
  disabled,
}: {
  teams: TeamView[];
  scopeTeams: string[];
  onChange: (teams: string[]) => void;
  disabled: boolean;
}) {
  const allTeams = scopeTeams.length === 0;
  return (
    <div className="mt-4 rounded border border-hairline p-3">
      <h3 className="mb-2 text-sm text-muted">Scope</h3>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="radio"
          checked={allTeams}
          onChange={() => onChange([])}
          disabled={disabled}
          aria-label="All teams"
        />
        All teams
      </label>
      <div className="mt-2 flex flex-wrap gap-3">
        {teams.map((team) => (
          <label key={team.id} className="flex items-center gap-1.5 text-sm text-muted">
            <input
              type="checkbox"
              checked={scopeTeams.includes(team.name)}
              disabled={disabled}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? [...scopeTeams, team.name]
                    : scopeTeams.filter((name) => name !== team.name),
                )
              }
            />
            {team.name}
          </label>
        ))}
      </div>
    </div>
  );
}

function Sandbox() {
  const { session } = useSession();
  const [text, setText] = useState("Email me at avery@example.com");
  const [result, setResult] = useState<PolicyTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.testPolicy(session.token, text));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run the test.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded border border-hairline p-3">
      <h3 className="mb-2 text-sm text-muted">Live test sandbox</h3>
      <Textarea
        rows={3}
        value={text}
        onChange={(event) => setText(event.target.value)}
        aria-label="Sandbox prompt"
      />
      <Button className="mt-2" variant="default" size="sm" onClick={run} disabled={busy}>
        {busy ? "Testing..." : "Test prompt"}
      </Button>
      {error ? <p className="mt-2 text-sm text-blocked">{error}</p> : null}
      {result ? (
        <div className="mt-3 text-sm">
          <p className="text-muted">The model would receive:</p>
          <pre className="mt-1 overflow-auto rounded border border-hairline bg-canvas p-2 font-mono text-xs">
            {result.masked_text ?? "(blocked - nothing is forwarded)"}
          </pre>
          <p className="mt-2 text-muted">{result.findings.length} findings:</p>
          <ul className="mt-1 flex flex-col gap-1">
            {result.findings.map((finding, index) => (
              <li key={index} className="text-xs">
                {finding.entity_type} - <span className="font-mono">{finding.action}</span>{" "}
                (confidence <span className="font-mono">{finding.confidence.toFixed(2)}</span>)
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function VersionHistory({
  versions,
  mayWrite,
  yaml,
  onActivate,
}: {
  versions: PolicyVersions | null;
  mayWrite: boolean;
  yaml: string;
  onActivate: (version: number) => Promise<void>;
}) {
  const exportYaml = () => {
    const blob = new Blob([yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "frostglass-policy.yaml";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded border border-hairline p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm text-muted">Version history</h3>
        <Button variant="ghost" size="sm" onClick={exportYaml}>
          Export as YAML
        </Button>
      </div>
      {versions === null ? (
        <LoadingState label="Loading versions" />
      ) : (
        <ul className="flex flex-col gap-1">
          {[...versions.versions].reverse().map((version) => (
            <li key={version.version} className="flex items-center justify-between text-sm">
              <span>
                Version <span className="font-mono">{version.version}</span>
                {version.version === versions.active_version ? " (active)" : ""}
              </span>
              {mayWrite && version.version !== versions.active_version ? (
                <Button variant="ghost" size="sm" onClick={() => onActivate(version.version)}>
                  Roll back to this
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
