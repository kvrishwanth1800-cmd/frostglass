# Changelog

## Unreleased

### Added
- M3 masking engine with format-preserving surrogates, scoped AES-GCM vault mappings, TTL purge, and five masking modes.
- Non-streaming restoration and rolling-buffer streamed restoration with exhaustive three-chunk boundary coverage.
- Gateway masking before provider routing and vault initialization from `FG_VAULT_ENCRYPTION_KEY`.
- M4 SQLite-backed immutable policy versions and durable per-team shadow-mode settings.
- M4 precedence engine (H.4): block first, then user/team/model/global scope, then most restrictive action.
- M4 dry-run `POST /admin/policy/test` endpoint that runs detect/decide/mask with no provider call.

### Changed
- Gateway decision objects and responses now carry the active policy version (`X-Frostglass-Policy-Version`).
- New teams default to shadow mode from the policy store. M5 will persist policy versions and counterfactual decisions in its audit schema.
- Application factory `create_app()` now builds all per-app dependencies fresh and each route module exposes a `create_router(...)` factory returning a new router bound to that app instance.

### Fixed
- **Router isolation:** removed module-level router singletons that carried request-handling state across app instances, which caused a second `create_app()` in the same process to dispatch through an earlier app's handler state. Routers are now constructed per app via `create_router(...)`. Regression test: `tests/integration/test_detection_lifecycle.py::test_app_instances_use_their_own_policy_databases`.
- **Per-entity-type decisions:** each finding is now decided independently on its own entity type and confidence instead of one decision collapsing across all findings. Regression test: `tests/integration/test_per_finding_decisions.py::test_same_type_findings_get_independent_decisions`.
- **CI memory-pressure runner kill:** the four extraction-security tests each built their own app, and `build_detection_engine()` loads a fresh ~650MB spaCy model per call, stacking resident model copies and killing the runner. Now share one module-scoped app/engine across those tests (commit `ea6eaac`). Test-side only; production lifecycle tracked in issue #22.

### Security
- **Extraction leak paths closed.** The gateway extractor now scans every prompt-bearing field. Previously unscanned surfaces that could leak secrets to providers, each now blocked (HTTP 403 `policy_blocked`, secret never echoed) and regression-tested in `tests/integration/test_extraction_security.py`:
  - OpenAI `/v1/embeddings` `input`.
  - Anthropic `/v1/messages` `tool_use.input`.
  - Anthropic `/v1/messages` `tool_result.content`.
  - Tool/function JSON-schema `default` values (gap found proactively during review).
- **Default block ruleset** now covers AWS_ACCESS_KEY, GITHUB_TOKEN, SLACK_TOKEN, STRIPE_KEY, OPENAI_KEY, ANTHROPIC_KEY, JWT, PRIVATE_KEY, HIGH_ENTROPY_TOKEN, and PASSWORD at confidence >= 0.7 (`frostglass/policy/defaults.py`).
- Application startup refuses missing or invalid vault encryption configuration.
- Tenant-wide stable mapping remains explicitly documented as high re-identification risk.
- Detection-engine model lifecycle (single cached model) flagged for M8 hardening; tracked in issue #22.

## M2
- Final detection engine implementation merged in PR #17. It superseded the incomplete early M2 snapshot in PR #16.
