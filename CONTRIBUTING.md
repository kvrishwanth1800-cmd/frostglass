# Contributing to Frostglass

## Development setup

Use Python 3.11 or later. Create and activate a virtual environment, then install the development dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

Set strong, temporary environment values before running the app or tests:

```bash
export FG_VAULT_ENCRYPTION_KEY="$(python -c 'import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
export FG_TENANT_SALT="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Run checks with `make test`, `make lint`, and `make typecheck`.

## Pull requests

Use conventional commits. Keep changes in milestone scope. Include tests for behavior changes. Update `STATUS.md` and `CHANGELOG.md` in every commit. Do not commit secrets or real personal data.

## First contribution

Adding a detector will be a supported first contribution after the detection engine arrives in M2. It must include synthetic corpus coverage and accuracy measurements.
