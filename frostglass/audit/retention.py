"""Nightly retention purge for audit rows and captured content (H.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from frostglass.audit.store import AuditStore


class RetentionPurger:
    """Purge audit rows past their retention window and expired captures."""

    def __init__(
        self, store: AuditStore, audit_retention_days: int, capture_retention_days: int
    ) -> None:
        self._store = store
        self._audit_retention_days = audit_retention_days
        self._capture_retention_days = capture_retention_days

    def purge(self, now: datetime | None = None) -> None:
        """Delete requests older than the audit window and expired captures."""
        moment = now or datetime.now(UTC)
        audit_cutoff = moment - timedelta(days=self._audit_retention_days)
        self._store.purge(audit_cutoff=audit_cutoff, now=moment)
