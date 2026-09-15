# Build Status

**Current milestone:** M3 - Masking engine, validation in progress
**Branch:** m3-masking-engine
**Last updated:** 2026-09-14

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [ ] M3 Masking engine - implementation complete, CI validation pending
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M3 task state
- [x] Format-preserving surrogate generators per entity type
- [x] Request, session, and tenant consistency scopes
- [x] AES-GCM encrypted in-memory vault with TTL
- [x] Non-streaming and rolling-buffer streaming restoration
- [x] Five masking modes: allow, pseudonymize, tag, hash, and block
- [x] Gateway request masking and non-stream response restoration
- [x] Application vault initialization from `FG_VAULT_ENCRYPTION_KEY`
- [x] Startup coverage for missing vault-key refusal
- [ ] M3 acceptance-test CI validation

## M2 merge history
- PR #16 merged an incomplete early M2 snapshot directly to main. PR #17 superseded it with the final validated M2 implementation.

## Notes for the next session
- M3 streaming restoration keeps a rolling tail based on the longest surrogate and exhaustively tests all valid two-boundary three-chunk splits of `Marcus Feld`.
- Tenant consistency scope has a high re-identification risk. It is available but not the default.
- CI must use mock providers only. Never call vendor APIs in tests.
