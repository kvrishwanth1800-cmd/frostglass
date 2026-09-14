# Build Status

**Current milestone:** M2 - Detection engine, ready for review
**Branch:** m2-detection
**Last updated:** 2026-09-10

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Pending review in PR #17.
- [ ] M3 Masking engine
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M2 completion evidence
- [x] Structural recognizers with validation
- [x] Secret recognizers and entropy heuristics
- [x] Aho-Corasick dictionary matching
- [x] Presidio and spaCy NER recognition
- [x] Sorted, disjoint span merging and raw-value-safe findings
- [x] Gateway detection lifecycle integration
- [x] Synthetic golden corpus and detection scoring harness
- [x] spaCy model cache and CI detection accuracy gate
- [x] M2 self-check and pull request

## M2 accuracy results
- Structured entity recall: 100.00% (target >=98%)
- Dictionary entity recall: 100.00% (target >=99%)
- NER recall: PERSON 87.50%, LOCATION 100.00%, ORGANIZATION 100.00% (target >=85%)
- Overall precision: 94.44% (target >=90%)
- Clean-control false-positive rate: 0.00% (0/2 examples, target <=2%)

## Open decisions / blockers
- Branch protection temporarily does not require approvals or CODEOWNERS review because the repository has one owner. Re-enable both controls before outside contributors join.

## Notes for the next session
- M2 is complete and ready for review in `m2-detection`. The gateway scans all extracted request text before provider routing and holds safe, location-associated findings in request context. The OpenAI-compatible integration test covers a card in a system message and an AWS access key in tool-call arguments, using only the mock provider.
- The clean-control corpus contains two examples. Its 0/2 false-positive result passes the M2 target but has limited statistical strength. Expand the clean-control corpus in a later milestone.
- `pyahocorasick` is a declared runtime dependency but does not publish typing metadata. Mypy suppresses only its missing-import error.
- CI caches the pinned `en_core_web_lg` 3.7.1 wheel by Python version. The model URL is one unbroken argument in both test and detection-accuracy jobs.
- CI must use mock providers only. Never call vendor APIs in tests.
