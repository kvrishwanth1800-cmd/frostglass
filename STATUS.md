# Build Status

**Current milestone:** M2 - Detection engine
**Branch:** m2-detection
**Last updated:** 2026-09-10

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [ ] M2 Detection engine - IN PROGRESS
- [ ] M3 Masking engine
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M2 task state
- [x] Structural recognizers with validation
- [x] Secret recognizers and entropy heuristics
- [x] Aho-Corasick dictionary matching
- [x] Presidio and spaCy NER recognition
- [x] Sorted, disjoint span merging and raw-value-safe findings
- [ ] Gateway detection lifecycle integration
- [x] Synthetic golden corpus and detection scoring harness
- [x] spaCy model cache and CI detection accuracy gate
- [ ] M2 self-check and pull request

## Open decisions / blockers
- Branch protection temporarily does not require approvals or CODEOWNERS review because the repository has one owner. Re-enable both controls before outside contributors join.

## Notes for the next session
- M2 is active on `m2-detection`. All four detector layers and a synthetic corpus scorer exist. Corpus adversarial coverage explicitly includes obfuscated email, spaced card, and an embedded-name code identifier.
- `pyahocorasick` is a declared runtime dependency but does not publish typing metadata. Mypy suppresses only its missing-import error.
- CI caches the pinned `en_core_web_lg` 3.7.1 wheel by Python version. The model URL is one unbroken argument in both test and detection-accuracy jobs.
- The M1 mock provider is network-free and its OpenAI and Anthropic SSE formats are CI-verified. Keep it as the test upstream for M2. M2 detectors must run against real gateway request and response payload shapes, including streaming payloads.
- CI must use mock providers only. Never call vendor APIs in tests.
- Mypy strict mode is scoped to detection, masking, and policy modules. M2 detection modules must pass strict mode.
