# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- Secure startup configuration validation and health endpoint.
- Docker Compose secret initialization for local development.
- Contributor, security, and code-of-conduct documentation.
- Pull request and issue templates.
- GitHub Actions quality, security, dependency-audit, and release workflows.
- Dashboard build foundation and milestone directory tree.
- Package markers for the strict typecheck modules.
- A production dependency manifest for the dependency audit.
- Detection engine foundations with raw-value-safe findings and span merging.
- Structural validation and secret detection layers.
- Aho-Corasick dictionary detection for company-specific terms.
- Presidio and spaCy named-entity recognition.
- Synthetic golden corpus and detection scoring harness.
- Cached spaCy model setup and a CI detection accuracy gate.
- Gateway lifecycle detection that scans every extracted request text value before provider routing.
- Mock-provider integration coverage for sensitive system-message and tool-call argument content.

### Fixed
- Python package discovery now excludes the dashboard from backend builds.
- Strict type checking is scoped to the required detection, masking, and policy modules.
- Dependency audit resolves the declared production dependency set, excluding the audit tool's own environment.
- Runtime dependencies can resolve patched compatible releases during security audits.
- spaCy model installation now uses one valid URL and Aho-Corasick has a scoped mypy import override.
- Entropy recognition suppresses candidates that overlap a known-format secret.
- The NER plumbing test uses an unambiguous person name. The golden corpus retains the ambiguous Avery Stone case for recall measurement.

### Changed
- Started M2 detection engine implementation.
