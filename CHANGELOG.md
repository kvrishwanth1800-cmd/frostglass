# Changelog

## Unreleased

### Added
- M3 masking engine with format-preserving surrogates, scoped AES-GCM vault mappings, TTL purge, and five masking modes.
- Non-streaming restoration and rolling-buffer streamed restoration with exhaustive three-chunk boundary coverage.
- Gateway masking before provider routing and vault initialization from `FG_VAULT_ENCRYPTION_KEY`.
- M4 SQLite-backed immutable policy versions and durable per-team shadow-mode settings.
- M4 precedence engine (H.4): block first, then user/team/model/global scope, then most restrictive action.
- M4 dry-run `POST /admin/policy/test` endpoint that runs detect/decide/mask with no provider call.
- M5 durable audit layer (`frostglass/audit/`): requests, findings, and decision traces persisted with policy version and the shadow counterfactual, storing only offsets, entity types, salted value hashes, and decisions - never raw prompt content (H.5, ADR 0002).
- M5 append-only `audit_events` table with UPDATE/DELETE triggers so admin actions cannot be edited or erased through the application.
- M5 optional encrypted content capture, off by default (`FG_CONTENT_CAPTURE`), storing the masked payload only with a short TTL and skipped entirely in shadow mode.
- M5 retention purge job (`FG_AUDIT_RETENTION_DAYS` default 90, `FG_CAPTURE_RETENTION_DAYS` default 7).
- M5 gateway request recording (allowed/masked/shadow/blocked) with the audit request id returned as `X-Frostglass-Request-Id`.
- M5 Admin API surface (`/admin/*`): stats overview, requests and per-request decision traces, finding false-positive reporting, policy read/create/activate/test, teams/users/keys management, detectors, dictionaries, suggestions, settings, and the audit-event log - with cursor pagination and published OpenAPI at `/admin/docs`.
- M5 server-side RBAC (`AdminIdentity`/`Permission`/`Role`) enforced on every `/admin` endpoint, covered by AC-M5-02 negative tests (`tests/integration/test_admin_rbac.py`).
- M5 admin list endpoints hold p95 < 300 ms over 10k synthetic requests (`tests/integration/test_admin_perf.py`, AC-M5-01).

### Changed
- Gateway decision objects and responses now carry the active policy version (`X-Frostglass-Policy-Version`).
- New teams default to shadow mode from the policy store.
- Application factory `create_app()` now builds all per-app dependencies fresh (including the audit store and recorder on `app.state`) and each route module exposes a `create_router(...)` factory returning a new router bound to that app instance.

### Fixed
- **Router isolation:** removed module-level router singletons that carried request-handling state across app instances. Regression test: `tests/integration/test_detection_lifecycle.py::test_app_instances_use_their_own_policy_databases`.
- **Per-entity-type decisions:** each finding is decided independently on its own entity type and confidence. Regression test: `tests/integration/test_per_finding_decisions.py::test_same_type_findings_get_independent_decisions`.
- **CI memory-pressure runner kill:** share one module-scoped app/engine across the extraction-security tests (commit `ea6eaac`). Test-side only; production lifecycle tracked in issue #22.

### Security
- **Extraction leak paths closed.** The gateway extractor scans every prompt-bearing field. Regression-tested in `tests/integration/test_extraction_security.py`: OpenAI `/v1/embeddings` `input`; Anthropic `/v1/messages` `tool_use.input` and `tool_result.content`; tool/function JSON-schema `default` values.
- **Default block ruleset** covers AWS_ACCESS_KEY, GITHUB_TOKEN, SLACK_TOKEN, STRIPE_KEY, OPENAI_KEY, ANTHROPIC_KEY, JWT, PRIVATE_KEY, HIGH_ENTROPY_TOKEN, and PASSWORD at confidence >= 0.7.
- **Audit database never stores raw content.** With capture disabled, an automated test seeds known synthetic values across entity types through the full pipeline and confirms none appear in any DB column (`tests/integration/test_no_raw_values_in_db.py`, AC-M5-03).
- **Cross-team isolation (no IDOR).** `/admin` request and trace lookups are team-scoped; a request that exists outside the caller's team returns 404 rather than 403, so existence is never leaked across teams (`tests/integration/test_admin_idor.py`, AC-M5-05).
- Application startup refuses missing or invalid vault encryption configuration.
- Detection-engine model lifecycle (single cached model) flagged for M8 hardening; tracked in issue #22.

## M2
- Final detection engine implementation merged in PR #17. It superseded the incomplete early M2 snapshot in PR #16.
