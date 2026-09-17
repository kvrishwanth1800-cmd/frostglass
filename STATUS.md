# Build Status

**Current milestone:** M4 - Policy engine and shadow mode, COMPLETE (merging PR #19)
**Branch:** m4-policy
**Last updated:** 2026-09-17

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. CI passed on Python 3.11 and 3.12.
- [x] M4 Policy engine + shadow mode - COMPLETE. CI green on 3.11 and 3.12; merging PR #19.
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M4 task state
- [x] Typed rule model, YAML parsing, default secret blocking policy, and precedence rules
- [x] SQLite-backed immutable policy-version storage
- [x] Durable per-team shadow-mode setting, with shadow enabled for new teams
- [x] Thread active policy version through per-finding and per-request decisions
- [x] Dry-run policy endpoint without provider calls
- [x] ADR 0002 records the M4/M5 persistence boundary
- [x] Security review findings fixed with regression tests (see M4 security review)
- [x] Router-isolation architecture bug fixed (see M4 engineering history)
- [x] Full CI green on 3.11 and 3.12; memory-pressure runner kill root-caused and fixed

## M4 Definition of Done scope
- AC-M4-01 (precedence covers every ordering pair): `tests/unit/test_policy_precedence.py::test_ac_m4_01_precedence_covers_every_ordering_pair`, 5x5 actions x 4x4 scopes = 400 combinations.
- AC-M4-02 (shadow forwards original payload, logs counterfactual): `tests/test_policy_acceptance.py::test_ac_m4_02_shadow_mode_forwards_original_payload_and_threads_counterfactual`.
- AC-M4-03 (policy version on every request): response header `X-Frostglass-Policy-Version`, carried by `FindingDecision` and `GatewayRequestContext`; `tests/test_policy_acceptance.py::test_ac_m4_03_gateway_threads_active_policy_version`.
- AC-M4-04 (dry-run returns findings, decisions, rule IDs, masked text, no provider call): `tests/test_policy_acceptance.py::test_ac_m4_04_dry_run_returns_findings_decisions_rules_and_masked_text`.
- M5 owns durable request, finding, and audit-event persistence. Its first task is to persist policy versions and shadow counterfactual decisions without raw prompt content.

## M4 engineering history (permanent record)

### Precedence engine and shadow mode
Typed rule/scope/action/decision models with immutable, SQLite-backed policy versions (append-only). Precedence follows H.4: block first, then user/team/model/global scope, then most restrictive action. `PolicyEngine.evaluate` (`frostglass/policy/engine.py`) returns one `FindingDecision` per finding, each carrying the ruleset version. Per-team shadow mode is durable (`FG_POLICY_DATABASE_PATH`, default `frostglass-policy.sqlite3`); new teams default to shadow=True until an explicit stored setting disables it. Shadow forwards the original payload while still computing and recording the counterfactual decision. `POST /admin/policy/test` runs the full detect/decide/mask path with no provider call.

### Router-isolation architecture bug and fix
Earlier structure built the FastAPI app at module level with shared, module-level router singletons. Because those routers held request-handling state (key store, limits, provider registry, tenant salt) bound at import, a second `create_app()` in the same process dispatched through the first app's handler state, i.e. stale/cross-app dispatch. Fix: `create_app()` (`frostglass/main.py`) now builds all per-app dependencies fresh each call (Settings, EncryptedVault, MaskingEngine, ProviderRegistry, policy engine, key store, limits) and each route module exposes a `create_router(...)` factory that returns a new `APIRouter()` bound to that one instance (`frostglass/gateway/routes_openai.py`, `routes_anthropic.py`, `admin/routes_policies.py`). No router state is shared across app instances. Regression: `tests/integration/test_detection_lifecycle.py::test_app_instances_use_their_own_policy_databases` proves a later app-factory call does not dispatch through an earlier app's routes. This precedent (that `create_app()` can run more than once per process) is why issue #22 treats the per-call model load as a real production memory concern.

### Security review findings (B.2 adversarial + B.3 security gate) and fixes
The gateway extractor (`frostglass/gateway/extract.py`) previously walked only a subset of prompt-bearing fields, leaving secret/PII leak paths. Findings, all fixed and regression-tested in `tests/integration/test_extraction_security.py`:
1. **Embeddings `input` not scanned** (`/v1/embeddings`). Secrets in the embeddings input reached the provider unmasked. Fixed: extractor now walks every string leaf in the payload tree. Test: `test_embeddings_input_secret_is_blocked`.
2. **Anthropic `tool_use.input` not scanned** (`/v1/messages`). Secrets inside a tool-use input object leaked. Fixed and tested: `test_anthropic_tool_use_input_secret_is_blocked`.
3. **Anthropic `tool_result.content` not scanned**. Secrets inside tool-result content leaked. Fixed and tested: `test_anthropic_tool_result_content_secret_is_blocked`.
4. **Tool/function JSON-schema `default` field gap (found proactively).** A secret placed as a `default` value inside a tool parameter JSON schema was not scanned. Fixed: the extractor is now schema-agnostic and collects every string leaf including schema `default` values. Test: `test_tool_schema_default_secret_is_blocked`.
5. **Missing secret types in the default block rule.** The default block ruleset (`frostglass/policy/defaults.py`, `_SECRET_TYPES`) now covers AWS_ACCESS_KEY, GITHUB_TOKEN, SLACK_TOKEN, STRIPE_KEY, OPENAI_KEY, ANTHROPIC_KEY, JWT, PRIVATE_KEY, HIGH_ENTROPY_TOKEN, PASSWORD, blocked at confidence >= 0.7.
6. **Per-entity-type decision collapsing.** One decision was being applied across all findings. Fixed so each finding is decided independently on its own entity_type and confidence (`PolicyEngine.evaluate` -> `decide(...)` per finding in `frostglass/policy/precedence.py`). Regression: `tests/integration/test_per_finding_decisions.py::test_same_type_findings_get_independent_decisions`.

All blocked requests return HTTP 403 with error type `policy_blocked` and never echo the secret back in the response body.

### Memory-pressure CI failure, root cause, and fix
CI test jobs were being killed by a runner shutdown signal ~50s into pytest, as `tests/unit/test_detection_corpus.py` (loads spaCy `en_core_web_lg`) began. Re-running `main`'s last CI unmodified was fully green, ruling out pre-existing infra. Root cause: the four new tests in `tests/integration/test_extraction_security.py` each built their own `TestClient(create_app())`, and `build_detection_engine()` loads a fresh ~650MB spaCy model per call (no cache), so up to four resident model copies stacked with the corpus test's own load and exhausted the runner (OOM/kill, never an assertion failure). Fix (commit `ea6eaac`): a module-scoped shared `enforcing_client` fixture builds one app / one model load reused across all four tests. This is a test-side fix; production behavior is unchanged. After the fix, both test jobs run the full suite including the corpus test to completion (~61s / ~52s) with no kill. A temporary `-q` install diagnostic (commit `d1385e7`) was used to surface pytest output in the truncated log window and then reverted (commit `9b03691`).

## Flagged for later (not an M4 fix)
- Detection-engine model lifecycle: `build_detection_engine()` constructs a fresh `NerDetector`, which loads the ~650MB spaCy `en_core_web_lg` model on every call. Each `create_app()` therefore loads its own model copy. If `create_app()` runs more than once in a live process (which the M4 router-isolation precedent proves can happen under some reload/redeploy patterns), resident memory grows by ~650MB per call. Part N budgets <=1.5GB steady-state with the NER model loaded, which implies exactly one resident model instance. Formalize the detection-engine lifecycle (a single shared or cached model) in M8 hardening. Tracked in GitHub issue #22 (https://github.com/kvrishwanth1800-cmd/frostglass/issues/22). The test-side symptom is fixed with a shared module-scoped fixture; the underlying production concern remains open.

## M5 first priority
- [ ] Wire `policy_version` and counterfactual decision data into the durable audit persistence layer (per ADR 0002).

## Notes for the next session
- Policy snapshots and per-team shadow settings use `FG_POLICY_DATABASE_PATH`, defaulting to `frostglass-policy.sqlite3`.
- New teams are in shadow mode until an explicit stored setting disables it.
- CI must use mock providers only. Never call vendor APIs in tests.
