# ADR 0003: Audit and Admin API simplifications for M5

## Status
Accepted.

## Context
The build brief's target architecture for M5 names Postgres with asyncpg and
SQLAlchemy for durable storage, Redis for shared state, and OIDC sessions for
the Admin API. M1 through M4 did not adopt that stack. They used the standard
library `sqlite3` for durable state (the `PolicyStore`), an in-memory virtual
key store, and per-`create_app()` dependency injection. Introducing Postgres,
an async ORM, Redis, and an OIDC provider in M5 would be a large infrastructure
step that the current test and CI environment (network-free, mock providers,
in-process `TestClient`) does not support, and would diverge sharply from the
existing code without delivering new user-observable behavior.

## Decision
M5 stays on the established stack:

1. **Audit store on SQLite.** The audit layer (`requests`, `findings`,
   `captured_content`, append-only `audit_events`) uses a `sqlite3` store that
   mirrors `PolicyStore`: one connection per app, `PRAGMA foreign_keys = ON`,
   `executescript` schema, `:memory:` supported. Append-only is enforced with
   `BEFORE UPDATE`/`BEFORE DELETE` triggers on `audit_events`. The audit and
   admin data share one database file (`FG_AUDIT_DATABASE_PATH`).
2. **Admin auth via session tokens, not OIDC.** The Admin API authenticates
   with opaque session tokens resolved to a role, kept fully separate from the
   gateway's virtual keys. RBAC is enforced server-side on every endpoint
   through a permission matrix. This is the seam OIDC will plug into in M6; the
   contract the routes depend on (an `AdminIdentity` with a role) does not
   change when the token issuer does.

The `SQLAlchemy` dependency stays declared for a future migration but is unused.

## Consequences
- M5 ships durable audit persistence and the full Admin API surface without new
  infrastructure, and every acceptance test runs in-process against mock
  providers.
- Horizontal scale-out (multiple processes sharing one audit store) is not yet
  supported; that arrives with the Postgres/Redis migration. This mirrors the
  known single-process constraint already tracked for the policy store.
- Swapping SQLite for Postgres later is contained to the store classes, and
  swapping session tokens for OIDC is contained to session resolution, because
  routes depend only on the store interfaces and `AdminIdentity`.
