# Build Status

**Current milestone:** M7 - Detectors, dictionaries, suggestions, NOT STARTED
**Branch:** main after PR #24 merge
**Last updated:** 2026-09-21

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. CI passed on Python 3.11 and 3.12.
- [x] M4 Policy engine + shadow mode - complete. Merged in PR #19 (squash `993cf56`).
- [x] M5 Audit + Admin API - complete. Merged in PR #23 (squash `dfe22ef`).
- [x] M6 Dashboard - complete. Verified in PR #24.
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M6 delivery and evidence
- [x] Admin API expansion delivers server-side overview, top-user, detection-estimate, and false-positive aggregates; expanded team and settings management; and persisted request cost and latency fields.
- [x] Dashboard delivers Overview, Requests Explorer, Blocked and Flagged, Policy Editor, Access and Budgets, and Settings pages, with shared design tokens, RBAC-aware actions, and loading, empty, error, and permission states.
- [x] Page 3 reports a false positive against an individual finding ID and updates only that finding in the trace.
- [x] AC-M6-01: Overview identifies the most flagged sender this week.
- [x] AC-M6-02: Policy Editor previews PERSON pseudonymization before save.
- [x] AC-M6-03: Requests Explorer limits its API page and rendered table work for a 100k-record corpus.
- [x] AC-M6-04: Policy Editor supports keyboard-only rule editing and confirm-dialog navigation.
- [x] AC-M6-05: Dashboard outcome colour utility classes are limited to blocked, masked, and shadow outcomes.
- [x] Dashboard E2E: six Playwright tests passed in 14.2 seconds on 2026-09-21.
- [x] Main CI: lint with GitHub annotations, format, mypy, Python 3.11 and 3.12 tests, detection accuracy, and dashboard build/typecheck passed before closeout.

Gates: B.1 QA, B.4 UX, B.7 Product passed for M6.

## Notes for the next session
- Dashboard talks only to the Admin API (Part G), never the DB.
- CI must use mock providers only. Never call vendor APIs in tests.
- Keep `ruff check --output-format=github .` in CI so lint failures create GitHub annotations.
