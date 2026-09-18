# Build Status

**Current milestone:** M6 - Dashboard, IN PROGRESS
**Branch:** m6-dashboard
**Last updated:** 2026-09-17

## Milestone progress
- [x] M0 Repository foundation - complete. AC-M0 criteria passed. Merged in PR #1.
- [x] M1 Pass-through gateway - complete. AC-M1-01 through AC-M1-06 passed. Merged in PR #14.
- [x] M2 Detection engine - complete. Final implementation merged in PR #17.
- [x] M3 Masking engine - complete. CI passed on Python 3.11 and 3.12.
- [x] M4 Policy engine + shadow mode - complete. Merged in PR #19 (squash `993cf56`).
- [x] M5 Audit + Admin API - complete. Merged in PR #23 (squash `dfe22ef`).
- [ ] M6 Dashboard - IN PROGRESS (this branch).
- [ ] M7 Detectors, dictionaries, suggestions
- [ ] M8 Hardening, docs, 1.0 release

## M6 acceptance criteria (Part K)
- AC-M6-01: a new user with no docs can find who sent the most flagged prompts this week.
- AC-M6-02: and can change PERSON from `allow` to `pseudonymize` with a preview before saving.
- AC-M6-03: requests table stays responsive at 100k rows.
- AC-M6-04: full keyboard navigation of the policy editor.
- AC-M6-05: colour appears only for policy outcomes.
Gates: B.1 QA, B.4 UX, B.7 Product.

## M6 task state

### Admin API expansion (backend, so pages query real server-side aggregates)
- [x] `stats_overview`: totals today/7d/30d, daily sparkline, outcome counts, sensitive %, top entity types, top teams and users by volume and flag rate, spend by provider/model (GROUP BY over existing indexes).
- [x] `detection_estimates`: per-entity confidence buckets so the policy editor confidence slider shows "matched N times in the last 7 days" and can estimate save impact.
- [x] `false_positive_rate`: findings reported / total, for the Blocked page widget.
- [x] Request view exposes prompt_tokens, completion_tokens, cost_cents, provider_latency_ms, fallback_used (persisted since M5).
- [x] Teams gain allowed_models; `PATCH /admin/teams/{id}` for shadow-mode / budget / rate-limit / allowed-models edits (Access page).
- [x] Settings gain SSO config and vault-key rotation timestamp; provider vendor keys stored write-only (last4 only, never the secret).
- [ ] Backend tests for every new endpoint + RBAC negative coverage.

### Dashboard pages (H.6.2), design tokens (H.6.1)
- [ ] Scaffold: Tailwind + shadcn/ui + Recharts + TanStack Table, IBM Plex Sans/Mono, tokens.css signal colours, left-rail layout, API client, RBAC context, dark + light.
- [ ] Page 1 Overview - live outcome ledger (last 200 requests), totals + sparkline, sensitive %, outcome counts, top entity types, top teams/users, spend, shadow-mode banner.
- [ ] Page 2 Requests explorer - virtualised TanStack table, filters, detail drawer with full decision trace, CSV export.
- [ ] Page 3 Blocked and flagged - blocked feed newest first, plain-language reason, never the secret, mark false positive, false-positive-rate widget.
- [ ] Page 4 Policy editor - matrix view, confidence slider with live estimate, scope selector, live test sandbox, diff and confirm before save, version history with rollback, export YAML.
- [ ] Page 7 Access and budgets - users, teams, roles, key issue/rotate/revoke (full key once), per-team budget/rate/allowed-models/shadow toggle.
- [ ] Page 8 Settings - provider keys (write-only), retention, content-capture toggle with risk confirm, SSO/OIDC, vault key status and rotation.
- [ ] Loading / empty / error / permission states on every list and table.
- [ ] RBAC-aware UI (hide actions a role's permission gates; server-side M5 remains the real boundary).

### Acceptance (Part L.1 Playwright)
- [ ] AC-M6-01 most-flagged user this week, no docs.
- [ ] AC-M6-02 change PERSON allow -> pseudonymize with preview before save.
- [ ] AC-M6-03 requests table responsive at 100k rows.
- [ ] AC-M6-04 full keyboard navigation of the policy editor.
- [ ] AC-M6-05 colour only for policy outcomes.

## Notes for the next session
- The M5 `requests` table already persists prompt_tokens, completion_tokens, cost_cents, provider_latency_ms, fallback_used, and findings carry entity_type/confidence/matched_rule_id/false_positive_reported, so every M6 aggregate is a GROUP BY over existing columns - no request/finding migration was needed.
- Net-new schema for M6: teams.allowed_models, settings SSO + vault-rotation columns, provider_credentials table (write-only vendor keys). Added defensively via ADD COLUMN so existing dev DBs migrate.
- Request action values are exactly allowed / masked / blocked / shadow; these map one-to-one to the H.6.1 signal colours. "Flagged" = action != allowed.
- Dashboard talks only to the Admin API (Part G), never the DB. Seeded admin session tokens per role remain fg-admin-{owner,admin,auditor,viewer}-token; gateway key fg-live-test-key -> test-team.
- CI must use mock providers only. Never call vendor APIs in tests.
