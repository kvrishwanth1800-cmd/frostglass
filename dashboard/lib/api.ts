"use client";

// Typed Admin API client. The dashboard talks ONLY to the Admin API (Part G),
// never to the database. Every method sends the session bearer token and maps
// non-2xx responses to a typed ApiError so pages can render a real error state
// with a message the operator can act on.

import type {
  DetectionEstimates,
  FalsePositiveRate,
  IssuedKey,
  KeyRow,
  PolicyTestResult,
  PolicyVersions,
  RequestsPage,
  RuleSetView,
  SettingsView,
  StatsOverview,
  TeamView,
  TopUsers,
  TraceResponse,
  UserRow,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_ADMIN_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  token: string,
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Cannot reach the Admin API. Check that the gateway is running.");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    if (response.status === 401) detail = "Your session is not valid. Sign in again.";
    else if (response.status === 403) detail = "Your role does not allow this action.";
    else if (response.status === 404) detail = "Not found.";
    else {
      try {
        const body = await response.json();
        if (body?.error?.message) detail = body.error.message;
      } catch {
        /* keep the default detail */
      }
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  statsOverview: (token: string, range = "7d") =>
    request<StatsOverview>(token, `/admin/stats/overview?range=${range}`),
  topUsers: (token: string, range = "7d") =>
    request<TopUsers>(token, `/admin/stats/top-users?range=${range}`),
  detections: (token: string, range = "7d") =>
    request<DetectionEstimates>(token, `/admin/stats/detections?range=${range}`),
  falsePositives: (token: string, range = "7d") =>
    request<FalsePositiveRate>(token, `/admin/stats/false-positives?range=${range}`),
  requests: (token: string, params: { action?: string; cursor?: string; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.action) query.set("action", params.action);
    if (params.cursor) query.set("cursor", params.cursor);
    query.set("limit", String(params.limit ?? 100));
    return request<RequestsPage>(token, `/admin/requests?${query.toString()}`);
  },
  trace: (token: string, id: string) =>
    request<TraceResponse>(token, `/admin/requests/${encodeURIComponent(id)}/trace`),
  reportFalsePositive: (token: string, findingRequestId: string) =>
    request<{ finding_id: string }>(token, `/admin/findings/${encodeURIComponent(findingRequestId)}/false-positive`, {
      method: "POST",
    }),
  policies: (token: string) => request<RuleSetView>(token, `/admin/policies`),
  policyVersions: (token: string) => request<PolicyVersions>(token, `/admin/policies/versions`),
  createPolicy: (token: string, yaml: string) =>
    request<RuleSetView>(token, `/admin/policies`, {
      method: "POST",
      body: JSON.stringify({ yaml }),
    }),
  activatePolicy: (token: string, version: number) =>
    request<RuleSetView>(token, `/admin/policies/${version}/activate`, { method: "POST" }),
  testPolicy: (token: string, text: string) =>
    request<PolicyTestResult>(token, `/admin/policies/test`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  teams: (token: string) => request<{ items: TeamView[] }>(token, `/admin/teams`),
  updateTeam: (token: string, id: string, patch: Partial<TeamView>) =>
    request<TeamView>(token, `/admin/teams/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  users: (token: string) => request<{ items: UserRow[] }>(token, `/admin/users`),
  keys: (token: string) => request<{ items: KeyRow[] }>(token, `/admin/keys`),
  createKey: (token: string, team: string, name: string) =>
    request<IssuedKey>(token, `/admin/keys`, {
      method: "POST",
      body: JSON.stringify({ team, name }),
    }),
  revokeKey: (token: string, id: string) =>
    request<{ id: string; revoked: boolean }>(token, `/admin/keys/${encodeURIComponent(id)}/revoke`, {
      method: "POST",
    }),
  settings: (token: string) => request<SettingsView>(token, `/admin/settings`),
  updateSettings: (token: string, patch: Partial<SettingsView>) =>
    request<SettingsView>(token, `/admin/settings`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  setProviderCredential: (token: string, provider: string, secret: string) =>
    request<{ provider: string; key_last4: string }>(token, `/admin/settings/providers`, {
      method: "POST",
      body: JSON.stringify({ provider, secret }),
    }),
  rotateVaultKey: (token: string) =>
    request<{ vault_key_rotated_at: string }>(token, `/admin/settings/vault/rotate`, {
      method: "POST",
    }),
};
