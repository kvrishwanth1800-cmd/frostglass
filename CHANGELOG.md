# Changelog

## Unreleased

### Added
- M3 masking engine with format-preserving surrogates, scoped AES-GCM vault mappings, TTL purge, and five masking modes.
- Non-streaming restoration and rolling-buffer streamed restoration with exhaustive three-chunk boundary coverage.
- Gateway masking before provider routing and vault initialization from `FG_VAULT_ENCRYPTION_KEY`.
- M4 SQLite-backed immutable policy versions and durable per-team shadow-mode settings.

### Changed
- Gateway decision objects and responses now carry the active policy version.
- New teams default to shadow mode from the policy store. M5 will persist policy versions and counterfactual decisions in its audit schema.

### Security
- Application startup refuses missing or invalid vault encryption configuration.
- Tenant-wide stable mapping remains explicitly documented as high re-identification risk.

## M2
- Final detection engine implementation merged in PR #17. It superseded the incomplete early M2 snapshot in PR #16.
