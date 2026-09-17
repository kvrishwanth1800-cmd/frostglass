"""Role-based access control for the Admin API.

Admin authentication is separate from the gateway's virtual keys (H.7): the
Admin API uses opaque session tokens (a stand-in for the OIDC session M6 will
add). RBAC is enforced server-side on every endpoint. The permission matrix is
the single source of truth; routes ask for a permission, never a role.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from frostglass.errors import gateway_error


class Role(StrEnum):
    """Admin roles in increasing order of privilege."""

    VIEWER = "viewer"
    AUDITOR = "auditor"
    ADMIN = "admin"
    OWNER = "owner"


class Permission(StrEnum):
    """Discrete capabilities the Admin API gates on."""

    READ_STATS = "read_stats"
    READ_REQUESTS = "read_requests"
    READ_TRACE = "read_trace"
    READ_CAPTURED_CONTENT = "read_captured_content"
    READ_POLICY = "read_policy"
    WRITE_POLICY = "write_policy"
    READ_DETECTORS = "read_detectors"
    WRITE_DETECTORS = "write_detectors"
    READ_DICTIONARIES = "read_dictionaries"
    WRITE_DICTIONARIES = "write_dictionaries"
    READ_SUGGESTIONS = "read_suggestions"
    WRITE_SUGGESTIONS = "write_suggestions"
    REPORT_FALSE_POSITIVE = "report_false_positive"
    READ_ACCESS = "read_access"
    WRITE_ACCESS = "write_access"
    READ_SETTINGS = "read_settings"
    WRITE_SETTINGS = "write_settings"


# Reads available to every role, including viewer. Trace is deliberately
# excluded: it exposes per-finding detail, so it is granted only to auditor
# and above (AC-M5-02).
_READS = {
    Permission.READ_STATS,
    Permission.READ_REQUESTS,
    Permission.READ_POLICY,
    Permission.READ_DETECTORS,
    Permission.READ_DICTIONARIES,
    Permission.READ_SUGGESTIONS,
    Permission.READ_ACCESS,
    Permission.READ_SETTINGS,
}

# viewer: reads dashboards but never traces, captured content, or writes.
# auditor: viewer plus trace, captured content, and false-positive reporting; no writes.
# admin: full configuration except ownership-level access management.
# owner: everything.
_MATRIX: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset(_READS),
    Role.AUDITOR: frozenset(
        _READS
        | {
            Permission.READ_TRACE,
            Permission.READ_CAPTURED_CONTENT,
            Permission.REPORT_FALSE_POSITIVE,
        }
    ),
    Role.ADMIN: frozenset(
        _READS
        | {
            Permission.READ_TRACE,
            Permission.READ_CAPTURED_CONTENT,
            Permission.REPORT_FALSE_POSITIVE,
            Permission.WRITE_POLICY,
            Permission.WRITE_DETECTORS,
            Permission.WRITE_DICTIONARIES,
            Permission.WRITE_SUGGESTIONS,
            Permission.WRITE_SETTINGS,
        }
    ),
    Role.OWNER: frozenset(Permission),
}


def role_permissions(role: Role) -> frozenset[Permission]:
    """Return the permission set granted to a role."""
    return _MATRIX[role]


@dataclass(frozen=True, slots=True)
class AdminIdentity:
    """An authenticated admin principal resolved from a session token."""

    user_id: str
    tenant_id: str
    team: str
    role: Role

    @property
    def tenant_wide(self) -> bool:
        """Owners and admins see every team; lower roles are team-scoped."""
        return self.role in {Role.OWNER, Role.ADMIN}

    def can(self, permission: Permission) -> bool:
        return permission in _MATRIX[self.role]

    def require(self, permission: Permission) -> None:
        """Raise 403 unless this identity holds the permission."""
        if not self.can(permission):
            raise gateway_error(403, "Insufficient role for this action", "permission_error")
