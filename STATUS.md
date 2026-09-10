# Build Status

**Current milestone:** M1 - Pass-through gateway
**Branch:** m1-gateway
**Last updated:** 2026-09-09

## Milestone progress
- [x] M0 Repository foundation - merged in PR #1
- [ ] M1 Pass-through gateway - IN PROGRESS
- [ ] M2 Detection engine
- [ ] M3 Masking engine
- [ ] M4 Policy engine + shadow mode
- [ ] M5 Audit + Admin API
- [ ] M6 Dashboard
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M1 task state
- [ ] Gateway routes and upstream response fidelity for OpenAI and Anthropic
- [ ] End-to-end SSE streaming
- [ ] Request extraction and replacement for prompts and tool payloads
- [ ] Virtual-key authentication and principal resolution
- [ ] Provider registry, fallback chain, and fallback recording
- [ ] Per-key and per-team budgets and rate limits
- [ ] Metrics, traces, structured logs, and Frostglass response headers
- [ ] Mock provider and AC-M1 acceptance tests
- [ ] M1 self-check and pull request

## Open decisions / blockers
- Branch protection temporarily does not require approvals or code-owner review because the repository has one owner. Re-enable both controls before outside contributors join.

## Notes for the next session
- M0 merged in PR #1. Startup always validates `FG_VAULT_ENCRYPTION_KEY` and `FG_TENANT_SALT`; Docker Compose generates local values in ignored `.env.local`.
- M1 must preserve OpenAI and Anthropic request, response, error, and SSE behavior. CI must use the mock provider only, never vendor APIs.
- Mypy strict mode remains scoped to detection, masking, and policy until those implementation milestones begin.
