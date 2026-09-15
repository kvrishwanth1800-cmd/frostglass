# Build Status

**Current milestone:** M4 - Policy engine and shadow mode, IN PROGRESS
**Branch:** m4-policy
**Last updated:** 2026-09-15

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. Merged in PR #18.
- [ ] M4 Policy engine + shadow mode - IN PROGRESS
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M4 task state
- [ ] Rule, scope, action, decision, and version models
- [ ] YAML loader and immutable in-memory policy-version store
- [ ] Precedence: block, scope specificity, then action restrictiveness
- [ ] Per-team shadow mode forwarding and counterfactual recording
- [ ] `POST /admin/policy/test` dry-run endpoint
- [ ] AC-M4-01 exhaustive precedence-pair tests
- [ ] AC-M4-02 shadow mode gateway test
- [ ] AC-M4-03 request policy-version recording test
- [ ] AC-M4-04 dry-run response and no-provider-call test

## Notes for the next session
- M4 starts from M3 merge commit `d3e60ce` on main.
- The current gateway has in-memory principals, detection, and masking. It has no database or audit module. M4 will use an immutable in-memory version store and request decision context until M5 persistence.
- CI must use mock providers only. Never call vendor APIs in tests.
