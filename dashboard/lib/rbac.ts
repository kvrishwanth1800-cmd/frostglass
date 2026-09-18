// UI-side mirror of the server RBAC matrix (frostglass/admin/rbac.py). This is
// used ONLY to hide actions a role cannot perform, so the interface never
// offers a button that would 403. The server remains the real boundary (H.6,
// H.7): every gated endpoint re-checks the permission regardless of the UI.

export type Role = "viewer" | "auditor" | "admin" | "owner";

export type Permission =
  | "read_stats"
  | "read_requests"
  | "read_trace"
  | "read_policy"
  | "write_policy"
  | "read_access"
  | "write_access"
  | "read_settings"
  | "write_settings"
  | "report_false_positive";

const READS: Permission[] = [
  "read_stats",
  "read_requests",
  "read_policy",
  "read_access",
  "read_settings",
];

const MATRIX: Record<Role, Permission[]> = {
  viewer: [...READS],
  auditor: [...READS, "read_trace", "report_false_positive"],
  admin: [
    ...READS,
    "read_trace",
    "report_false_positive",
    "write_policy",
    "write_settings",
  ],
  owner: [
    ...READS,
    "read_trace",
    "report_false_positive",
    "write_policy",
    "write_access",
    "write_settings",
  ],
};

export function can(role: Role, permission: Permission): boolean {
  return MATRIX[role].includes(permission);
}

export const ROLES: Role[] = ["viewer", "auditor", "admin", "owner"];
