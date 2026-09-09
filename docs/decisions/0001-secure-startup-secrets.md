# ADR 0001: Validate generated development secrets at startup

## Status
Accepted

## Context
Frostglass must reject missing, malformed, default, or placeholder vault encryption keys and tenant salts. The local Docker quickstart must also work without manual secret setup.

## Decision
The application always validates `FG_VAULT_ENCRYPTION_KEY` and `FG_TENANT_SALT` during startup. There is no development bypass. `docker compose up` first runs an initialization service that generates strong random values once and writes them to the gitignored `.env.local` file. The application then loads those values through the same environment variables used in every deployment.

## Consequences
A missing or invalid secret stops every environment at boot. Developers get a one-command local startup without committing or sharing generated values.
