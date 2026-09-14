# Build Status

**Current milestone:** M3 - Masking engine
**Branch:** m3-masking-engine
**Last updated:** 2026-09-14

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [ ] M3 Masking engine - IN PROGRESS
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M3 task state
- [ ] Format-preserving surrogate generators per entity type
- [ ] Request, session, and tenant consistency scopes
- [ ] AES-GCM encrypted vault with TTL
- [ ] Non-streaming restoration
- [ ] Streaming restoration buffer and exhaustive split tests
- [ ] Five masking modes: allow, pseudonymize, tag, hash, and block
- [ ] M3 acceptance tests and self-check

## M2 merge history
- PR #16 merged an incomplete early M2 snapshot directly to main. PR #17 superseded it with the final validated M2 implementation.

## Notes for the next session
- M3 is active on `m3-masking-engine`. Implement H.3 in this order: surrogates, consistency and vault, restoration, then modes.
- DATE and DATE_TIME masking must use one constant offset per session. Do not randomize values independently.
- Streaming restoration must retain a dynamic tail equal to the longest current surrogate and flush it only at stream end.
- CI must use mock providers only. Never call vendor APIs in tests.
