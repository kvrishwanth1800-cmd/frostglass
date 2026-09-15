# Build Status

**Current milestone:** M4 - Policy engine and shadow mode, validation in progress
**Branch:** m4-policy
**Last updated:** 2026-09-15

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. Merged in PR #18.
- [ ] M4 Policy engine + shadow mode - validation in progress
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M4 task state
- [x] Rule, scope, action, decision, and version models
- [x] YAML loader and immutable in-memory policy-version store
- [x] Precedence: block, scope specificity, then action restrictiveness
- [x] Per-team shadow mode forwarding and counterfactual decision context
- [x] `POST /admin/policy/test` dry-run endpoint
- [x] AC-M4-01 exhaustive precedence-pair tests: 400 action-and-scope ordering pairs
- [x] AC-M4-02 shadow mode gateway lifecycle test
- [x] AC-M4-03 request policy-version header test
- [x] AC-M4-04 dry-run response and no-provider-call test
- [ ] CI validation

## Notes for the next session
- M4 uses an append-only in-memory policy version repository. M5 must replace it with the required SQLite/Postgres persistence and persist the recorded policy version with audit requests.
- New teams default to shadow mode in `PolicyStore.shadow_for_team`; gateway principals retain an explicit shadow-mode flag until team persistence arrives in M5.
- CI must use mock providers only. Never call vendor APIs in tests.
