"""AC-M5-04: the retention job purges audit rows and captures on schedule."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from frostglass.audit.models import RequestRecord
from frostglass.audit.retention import RetentionPurger
from frostglass.audit.store import AuditStore

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _record(store: AuditStore, request_id: str, ts: datetime) -> None:
    store.record_request(
        RequestRecord(
            id=request_id,
            tenant_id="default",
            team="team-a",
            user="user-a",
            ts=ts,
            model="mock-model",
            provider="openai",
            action="allowed",
            policy_version=1,
            shadow=False,
        )
    )


def test_ac_m5_04_requests_older_than_window_are_purged() -> None:
    store = AuditStore(":memory:")
    _record(store, "old", _NOW - timedelta(days=91))
    _record(store, "recent", _NOW - timedelta(days=1))

    RetentionPurger(store, audit_retention_days=90, capture_retention_days=7).purge(now=_NOW)

    assert store.get_request("default", "old") is None
    assert store.get_request("default", "recent") is not None


def test_ac_m5_04_expired_captured_content_is_purged() -> None:
    store = AuditStore(":memory:")
    _record(store, "kept", _NOW)
    store.record_request(
        RequestRecord(
            id="captured",
            tenant_id="default",
            team="team-a",
            user="user-a",
            ts=_NOW,
            model="mock-model",
            provider="openai",
            action="masked",
            policy_version=1,
            shadow=False,
        ),
        sealed_capture=(b"x" * 20, _NOW - timedelta(days=1)),
    )

    RetentionPurger(store, audit_retention_days=90, capture_retention_days=7).purge(now=_NOW)

    assert store.captured_content("captured") is None
    assert store.get_request("default", "captured") is not None
