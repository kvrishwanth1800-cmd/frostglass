# Changelog

## Unreleased

### Added
- M3 masking engine with format-preserving surrogates, scoped AES-GCM vault mappings, TTL purge, and five masking modes.
- Non-streaming restoration and rolling-buffer streamed restoration with exhaustive three-chunk boundary coverage.
- Gateway masking before provider routing and vault initialization from `FG_VAULT_ENCRYPTION_KEY`.

### Security
- Application startup refuses missing or invalid vault encryption configuration.
- Tenant-wide stable mapping remains explicitly documented as high re-identification risk.

## M2
- Final detection engine implementation merged in PR #17. It superseded the incomplete early M2 snapshot in PR #16.
