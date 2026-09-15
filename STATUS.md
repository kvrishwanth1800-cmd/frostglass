# Build Status

**Current milestone:** M3 - Masking engine, ready for merge
**Branch:** m3-masking-engine
**Last updated:** 2026-09-15

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. CI passed on Python 3.11 and 3.12.
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M3 acceptance evidence
- [x] AC-M3-01: `test_ac_m3_01_round_trip_restores_non_sensitive_text` verifies mask and restore preserve non-sensitive text.
- [x] AC-M3-02: `test_ac_m3_02_session_identity_is_stable_for_five_turns` verifies one surrogate remains stable across five session turns.
- [x] AC-M3-03: `test_restore_every_three_chunk_boundary` exhaustively covers every ordered pair of distinct chunk boundaries in `Hello Marcus Feld, your request is complete.`. It tests 903 three-chunk layouts, in addition to named mid-first-name, space-boundary, mid-last-name, character-by-character, and single-chunk cases.
- [x] AC-M3-04: `test_dates_use_one_constant_session_offset` verifies two dates ten days apart remain ten days apart after masking.
- [x] AC-M3-05: `test_ac_m3_05_surrogate_spans_are_immune` verifies generated surrogate spans are marked immune within the request.
- [x] AC-M3-06: `test_vault_ciphertext_is_unreadable_without_key` verifies encrypted vault content cannot be decrypted with a different AES-GCM key.

## M3 task state
- [x] Format-preserving surrogate generators per entity type
- [x] Request, session, and tenant consistency scopes
- [x] AES-GCM encrypted in-memory vault with TTL
- [x] Non-streaming and rolling-buffer streaming restoration
- [x] Five masking modes: allow, pseudonymize, tag, hash, and block
- [x] Gateway request masking and non-stream response restoration
- [x] Application vault initialization from `FG_VAULT_ENCRYPTION_KEY`
- [x] Startup coverage for missing vault-key refusal
- [x] M3 acceptance-test CI validation

## M2 merge history
- PR #16 merged an incomplete early M2 snapshot directly to main. PR #17 superseded it with the final validated M2 implementation.

## Notes for the next session
- M3 streaming restoration keeps a rolling tail based on the longest surrogate and exhaustively tests all valid two-boundary three-chunk splits of `Marcus Feld`.
- Tenant consistency scope has a high re-identification risk. It is available but not the default.
- CI must use mock providers only. Never call vendor APIs in tests.
