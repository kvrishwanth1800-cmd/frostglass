// Types mirror the Admin API response shapes verified against the M5/M6
// backend (frostglass/admin/routes_admin.py). No field here is invented; each
// maps to a real key in _request_view, _finding_view, _ruleset_view, or the
// stats aggregates added for M6.

export type Outcome = "allowed" | "masked" | "blocked" | "shadow";

export interface RequestView {
  id: string;
  team: string;
  user: string;
  ts: string;
  model: string;
  provider: string;
  action: Outcome;
  policy_version: number;
  shadow: boolean;
  blocked_reason: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_cents: number | null;
  latency_ms: number | null;
  provider_latency_ms: number | null;
  status_code: number | null;
  fallback_used: boolean | null;
}

export interface FindingView {
  id: string;
  entity_type: string;
  detector: string;
  confidence: number;
  span: [number, number];
  matched_rule_id: string | null;
  action: string;
  was_shadow: boolean;
  reason: string;
  false_positive_reported: boolean;
}

export interface RequestsPage {
  items: RequestView[];
  next_cursor: string | null;
}

export interface TraceResponse {
  request_id: string;
  trace: FindingView[];
}

export interface StatsOverview {
  range: string;
  sampled: number;
  by_action: Record<string, number>;
  totals: { today: number; last_7d: number; last_30d: number };
  windowed_total: number;
  sensitive_requests: number;
  sensitive_pct: number;
  sparkline: { day: string; count: number }[];
  top_entity_types: { entity_type: string; count: number }[];
  top_teams: { team: string; count: number; flagged: number }[];
  top_users: { user: string; count: number; flagged: number }[];
  spend_by_provider: { provider: string; cost_cents: number }[];
  spend_by_model: { model: string; cost_cents: number }[];
}

export interface TopUsers {
  range: string;
  items: { user: string; count: number; flagged: number }[];
}

export interface DetectionEstimates {
  range: string;
  by_entity_type: Record<string, { total: number; at_confidence: Record<string, number> }>;
}

export interface FalsePositiveRate {
  range: string;
  total: number;
  reported: number;
  rate: number;
}

export interface PolicyRule {
  id: string;
  entity_types: string[];
  action: string;
  min_confidence: number;
  reason: string;
}

export interface RuleSetView {
  version: number;
  default_action: string;
  shadow_mode: boolean;
  rules: PolicyRule[];
}

export interface PolicyVersions {
  active_version: number;
  versions: RuleSetView[];
}

export interface PolicyTestFinding {
  entity_type: string;
  confidence: number;
  detector: string;
  span: [number, number];
  action: string;
  rule_id: string | null;
  reason: string;
}

export interface PolicyTestResult {
  policy_version: number;
  findings: PolicyTestFinding[];
  masked_text: string | null;
}

export interface TeamView {
  id: string;
  name: string;
  shadow_mode: boolean;
  monthly_budget_cents: number;
  rate_limit_rpm: number;
  allowed_models: string[];
  content_capture_enabled: boolean;
}

export interface UserRow {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
  disabled_at: string | null;
}

export interface KeyRow {
  id: string;
  team: string;
  key_prefix: string;
  name: string;
  created_at: string;
  revoked_at: string | null;
}

export interface IssuedKey {
  id: string;
  key: string;
  key_prefix: string;
}

export interface ProviderCredential {
  provider: string;
  key_last4: string;
  updated_at: string;
}

export interface SettingsView {
  audit_retention_days: number;
  capture_retention_days: number;
  content_capture_enabled: boolean;
  sso_enabled: boolean;
  sso_provider: string | null;
  sso_client_id: string | null;
  vault_key_rotated_at: string | null;
  provider_credentials: ProviderCredential[];
}
