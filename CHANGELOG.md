# Changelog

## Unreleased

### Added
- M4 policy engine with typed rules, YAML loading, immutable version snapshots, and documented precedence.
- Per-team shadow decision handling and the `/admin/policy/test` no-provider dry-run endpoint.

### Security
- Policy precedence makes block rules win over all matching non-block rules.

## M3
- Format-preserving masking engine with scoped AES-GCM vault mappings, TTL purge, five masking modes, and stream restoration.
- Gateway masking before provider routing and vault initialization from `FG_VAULT_ENCRYPTION_KEY`.

## M2
- Final detection engine implementation merged in PR #17. It superseded the incomplete early M2 snapshot in PR #16.
