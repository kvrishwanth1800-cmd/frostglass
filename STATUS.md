# Build Status

**Current milestone:** M4 - Policy engine and shadow mode, in progress
**Branch:** m4-policy
**Last updated:** 2026-09-15

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. CI passed on Python 3.11 and 3.12.
- [ ] M4 Policy engine + shadow mode - IN PROGRESS
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
- [ ] Validate full CI, finish review gates, and merge PR #19

## M4 Definition of Done scope
- AC-M4-03 is satisfied in M4 by the response header and the policy version carried by `FindingDecision` and `GatewayRequestContext`.
- M5 owns durable request, finding, and audit-event persistence. Its first task is to persist policy versions and shadow counterfactual decisions without raw prompt content.

## M5 first priority
- [ ] Wire `policy_version` and counterfactual decision data into the durable audit persistence layer.

## Notes for the next session
- Policy snapshots and per-team shadow settings use `FG_POLICY_DATABASE_PATH`, defaulting to `frostglass-policy.sqlite3`.
- New teams are in shadow mode until an explicit stored setting disables it.
- CI must use mock providers only. Never call vendor APIs in tests.
