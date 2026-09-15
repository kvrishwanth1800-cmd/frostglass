# ADR 0002: Persist policy configuration in M4 and decision traces in M5

## Status
Accepted

## Context
M4 requires immutable, versioned policy evaluation and team-level shadow mode. M5 owns the audit schema for requests, findings, and audit events. Creating a temporary audit table in M4 would duplicate the M5 persistence model and risk storing unsafe data.

## Decision
M4 persists immutable policy snapshots and per-team shadow settings in the policy database. The gateway reads each team's stored shadow setting for every request. Each `FindingDecision` and gateway request context carries the active `policy_version`, and the gateway returns it in `X-Frostglass-Policy-Version`.

M5 will persist the request-level policy version and the shadow-mode counterfactual decision trace in its durable audit schema. It must never persist raw prompt content.

## Consequences
Policy configuration survives process restarts and a new team defaults to shadow mode. The decision data is already available at the gateway boundary for M5. M4 does not claim durable audit-event storage.
