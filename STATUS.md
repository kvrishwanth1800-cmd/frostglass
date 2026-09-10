# Build Status

**Current milestone:** M2 - Detection engine (not started)
**Branch:** main
**Last updated:** 2026-09-10

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [ ] M2 Detection engine
- [ ] M3 Masking engine
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M1 completion record
- [x] Gateway routes and upstream response fidelity for OpenAI and Anthropic
- [x] End-to-end SSE streaming
- [x] Request extraction and replacement for prompts and tool payloads
- [x] Virtual-key authentication and principal resolution
- [x] Provider registry, fallback chain, and fallback recording
- [x] Per-key and per-team budgets and rate limits
- [x] Metrics, traces, structured logs, and Frostglass response headers
- [x] Mock provider and AC-M1 acceptance tests
- [x] OpenAI and Anthropic SDK e2e tests over a loopback HTTP server
- [x] M1 self-check and pull request

## Open decisions / blockers
- Branch protection temporarily does not require approvals or CODEOWNERS review because the repository has one owner. Re-enable both controls before outside contributors join.

## Notes for the next session
- Start M2 from updated `main`. Do not reuse the deleted `m1-gateway` branch.
- The M1 mock provider is network-free and its OpenAI and Anthropic SSE formats are CI-verified. Keep it as the test upstream for M2. M2 detectors must run against real gateway request and response payload shapes, including streaming payloads.
- The SDK e2e tests start the application on loopback Uvicorn and use unmodified OpenAI and Anthropic clients with only `base_url` changed. Preserve these tests when changing gateway routes or SSE event formats.
- Startup always validates `FG_VAULT_ENCRYPTION_KEY` and `FG_TENANT_SALT`. Docker Compose generates local values in ignored `.env.local`.
- CI must use mock providers only. Never call vendor APIs in tests.
- Mypy strict mode remains scoped to detection, masking, and policy modules. M2 should add its detection modules to the existing strict scope.
