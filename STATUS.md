# Build Status

## Overnight summary

- **M7 built and tested so far:** isolated dictionary persistence service with term list/add/update/remove/CSV import and immediate matching; isolated suggestion generator for unpoliced detections, recurring unknown patterns, over-blocking, and context-loss warnings; detector and suggestion dashboard pages; unit coverage for CRUD, CSV/paste import, immediate matching, suggestion generation, and regex rejection cases.
- **M7 awaiting manual wiring:** `docs/pending-manual-edits.md` lists the exact required changes to `main.py`, `gateway/pipeline.py`, and `routes_admin.py` for live Admin API routes, next-request masking, and transactional Apply behavior.
- **M7 awaiting security review:** custom regex recognizers are blocked. `docs/regex-security-review.md` explains why the current ReDoS syntax filter is not sufficient to approve shipping the feature. Do not merge M7.
- **M8 preparation:** not started because the M7 regex-safety hard stop requires a security decision.
- **Release boundary:** no `v1.0.0` tag was created and no M9 work started.

**Current milestone:** M7 - Detectors, dictionaries, suggestions, BLOCKED FOR SECURITY REVIEW
**Branch:** m7-suggestions
**Last updated:** 2026-09-21

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. CI passed on Python 3.11 and 3.12.
- [x] M4 Policy engine + shadow mode - complete. Merged in PR #19 (squash `993cf56`).
- [x] M5 Audit + Admin API - complete. Merged in PR #23 (squash `dfe22ef`).
- [x] M6 Dashboard - complete. Verified in PR #24.
- [ ] M7 Detectors, dictionaries, suggestions - BLOCKED FOR SECURITY REVIEW.
- [ ] M8 Hardening, docs, 1.0 release - not started.

## M7 task state
- [x] Isolated dictionary persistence and immediate matching service.
- [x] Isolated custom-recognizer validation and safe-test service, pending security approval.
- [x] Isolated deterministic four-kind suggestion generator.
- [x] Detector and suggestion dashboard page shells.
- [x] Manual wiring specification for redacted application files.
- [ ] Wire dictionary terms into the gateway detection pipeline.
- [ ] Wire tenant-scoped M7 API routes and server-side RBAC.
- [ ] Implement transactional suggestion Apply against live policy and detector configuration.
- [ ] Run full AC-M7 integration and Playwright evidence.
- [ ] Open M7 PR for security review. Do not merge.

## Notes for the next session
- The hard stop is a regex-safety judgment call. Review `docs/regex-security-review.md` before modifying recognizer support.
- Do not wire or expose regex save/enable behavior until a reviewed ReDoS control is selected.
- `docs/pending-manual-edits.md` contains every known required redacted-file insertion. Any additional redacted-file modification must be escalated.
- No v1.0 release or M9 work is authorized.
