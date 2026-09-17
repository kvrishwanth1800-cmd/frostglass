# Build Status

**Current milestone:** M5 - Audit and Admin API, COMPLETE
**Branch:** m5-audit-admin
**Last updated:** 2026-09-17

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. CI passed on Python 3.11 and 3.12.
- [x] M4 Policy engine + shadow mode - complete. Merged in PR #19 (squash `993cf56`).
- [x] M5 Audit + Admin API - complete. Admin API, server-side RBAC, cross-team isolation, and the performance budget delivered on this branch; CI green on 3.11 and 3.12.
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M5 task state
- [x] Durable audit schema (requests, findings, captured_content, audit_events) per Part I, with indexes
- [x] `audit_events` append-only, enforced by UPDATE/DELETE triggers
- [x] Decision-trace persistence carrying policy_version and the shadow counterfactual (ADR 0002)
- [x] Optional encrypted content capture, off by default; stores masked payload only, never the original; skipped in shadow mode
- [x] Retention purge job (90d audit rows, 7d captured content)
- [x] Gateway records every request (allowed/masked/shadow/blocked) with the audit id returned as X-Frostglass-Request-Id
- [x] AC-M5-03 raw-value scan test (`tests/integration/test_no_raw_values_in_db.py`)
- [x] AC-M5-04 retention test (`tests/unit/test_audit_retention.py`)
- [x] Admin API: all `/admin/*` endpoints, cursor pagination, server-side RBAC, published OpenAPI at `/admin/docs`
- [x] AC-M5-02 RBAC negative tests (lower privilege rejected on every /admin endpoint) (`tests/integration/test_admin_rbac.py`)
- [x] AC-M5-05 IDOR tests (a user cannot fetch another team's request/finding by id) (`tests/integration/test_admin_idor.py`)
- [x] AC-M5-01 performance: 10k synthetic requests, every list endpoint p95 < 300 ms (`tests/integration/test_admin_perf.py`)

## M5 acceptance criteria (Part K)
- AC-M5-01: 10k synthetic requests, every list endpoint p95 < 300 ms.
- AC-M5-02: RBAC enforced server-side on every endpoint.
- AC-M5-03: with capture disabled, seeded corpus values appear in no DB column.
- AC-M5-04: retention job purges on schedule.
- AC-M5-05: no IDOR - user A cannot fetch user B's request.
Gates: B.1 QA, B.3 Security, B.5 Performance.

## M5 self-audit against the two M4-taught failure classes
- Shared/singleton state across app instances: the audit store and recorder are built fresh per `create_app()` and stored on `app.state`; no module-level singletons. Each app opens its own SQLite connection.
- Repeated instantiation of an expensive resource: the SQLite connection and cipher are created once per app, not per request. (The spaCy model concern remains tracked in issue #22.)

## M5 engineering history (permanent record)

### Three masked bugs found by the AC suites and fixed
- **AC-M5-02 (RBAC):** the viewer role wrongly held READ_TRACE, so a viewer could read decision traces. Removed READ_TRACE from the viewer read set; it is granted to AUDITOR, ADMIN, and OWNER only (`frostglass/admin/rbac.py`).
- **Dry-run 422:** `POST /admin/policies/test` declared its body as a typed model and rejected the free-form payload with 422. Changed to `body: dict[str, Any] = Body(...)`.
- **AC-M5-05 (IDOR):** `GET /admin/requests/{id}/trace` enforced READ_TRACE before the team-scoped lookup, so a cross-team caller probing a real request id received 403 (leaking existence) instead of 404. The handler now returns 404 for a request that exists in the tenant but outside the caller's team scope, before the permission gate; a genuinely unknown id still falls through to the permission check (viewer -> 403, owner -> 404), preserving AC-M5-02. The plain `GET /admin/requests/{id}` endpoint was already team-scoped and correct.

## M4 Definition of Done scope
- AC-M4-01 (precedence covers every ordering pair): `tests/unit/test_policy_precedence.py::test_ac_m4_01_precedence_covers_every_ordering_pair`, 5x5 actions x 4x4 scopes = 400 combinations.
- AC-M4-02 (shadow forwards original payload, logs counterfactual): `tests/test_policy_acceptance.py::test_ac_m4_02_shadow_mode_forwards_original_payload_and_threads_counterfactual`.
- AC-M4-03 (policy version on every request): response header `X-Frostglass-Policy-Version`, carried by `FindingDecision` and `GatewayRequestContext`; `tests/test_policy_acceptance.py::test_ac_m4_03_gateway_threads_active_policy_version`.
- AC-M4-04 (dry-run returns findings, decisions, rule IDs, masked text, no provider call): `tests/test_policy_acceptance.py::test_ac_m4_04_dry_run_returns_findings_decisions_rules_and_masked_text`.
- M5 owns durable request, finding, and audit-event persistence, delivered on this branch.

## M4 engineering history (permanent record)

### Precedence engine and shadow mode
Typed rule/scope/action/decision models with immutable, SQLite-backed policy versions (append-only). Precedence follows H.4: block first, then user/team/model/global scope, then most restrictive action. `PolicyEngine.evaluate` (`frostglass/policy/engine.py`) returns one `FindingDecision` per finding, each carrying the ruleset version. Per-team shadow mode is durable (`FG_POLICY_DATABASE_PATH`, default `frostglass-policy.sqlite3`); new teams default to shadow=True until an explicit stored setting disables it. Shadow forwards the original payload while still computing and recording the counterfactual decision. `POST /admin/policy/test` runs the full detect/decide/mask path with no provider call.

### Router-isolation architecture bug and fix
Earlier structure built the FastAPI app at module level with shared, module-level router singletons that held request-handling state bound at import, causing a second `create_app()` in the same process to dispatch through the first app's handler state. Fix: `create_app()` builds all per-app dependencies fresh each call and each route module exposes a `create_router(...)` factory returning a new `APIRouter()` bound to that one instance. Regression: `tests/integration/test_detection_lifecycle.py::test_app_instances_use_their_own_policy_databases`. This precedent (that `create_app()` can run more than once per process) is why issue #22 treats the per-call model load as a real production memory concern.

### Security review findings (B.2 adversarial + B.3 security gate) and fixes
The gateway extractor now walks every string leaf in the payload tree, closing four leak paths (embeddings input, Anthropic tool_use.input and tool_result.content, tool JSON-schema default). The default block ruleset (`_SECRET_TYPES`) covers AWS_ACCESS_KEY, GITHUB_TOKEN, SLACK_TOKEN, STRIPE_KEY, OPENAI_KEY, ANTHROPIC_KEY, JWT, PRIVATE_KEY, HIGH_ENTROPY_TOKEN, PASSWORD at confidence >= 0.7. Each finding is decided independently per entity type and confidence. Regressions in `tests/integration/test_extraction_security.py` and `tests/integration/test_per_finding_decisions.py`.

### Memory-pressure CI failure, root cause, and fix
The four extraction-security tests each built their own `TestClient(create_app())`, and `build_detection_engine()` loads a fresh ~650MB spaCy model per call, stacking resident copies with the corpus test and killing the runner. Fixed (commit `ea6eaac`) with a module-scoped shared `enforcing_client` fixture. Test-side only; production lifecycle tracked in issue #22.

## Flagged for later (not an M5 fix)
- Detection-engine model lifecycle: `build_detection_engine()` loads the ~650MB spaCy model on every call, so each `create_app()` loads its own copy. Part N budgets <=1.5GB steady-state, implying one resident model. Formalize a single shared/cached model in M8 hardening. Tracked in GitHub issue #22 (https://github.com/kvrishwanth1800-cmd/frostglass/issues/22).

## Notes for the next session
- Audit persistence lives in `frostglass/audit/` (store, recorder, capture, retention, models); the gateway records every request and returns the audit id as `X-Frostglass-Request-Id`.
- `FG_CONTENT_CAPTURE` defaults false; capture stores the masked payload only, encrypted, short TTL, and is skipped in shadow mode (the forwarded payload is the unmasked original there).
- `FG_AUDIT_DATABASE_PATH` defaults `frostglass-audit.sqlite3`; tests use `:memory:` via conftest.
- Admin API surface (`/admin/*`) is delivered with session auth separate from virtual keys, cursor pagination, server-side RBAC on every endpoint, and published OpenAPI at `/admin/docs`.
- Next: M6 dashboard.
- CI must use mock providers only. Never call vendor APIs in tests.
