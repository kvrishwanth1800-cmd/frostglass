# Frostglass

Self-hosted AI gateway and DLP proxy that detects and masks PII, secrets, and confidential data in LLM prompts before they leave your network.

> Frostglass is under active development. It is not yet ready for production use or legal-compliance claims.

## Status

Milestone M0 establishes the repository foundation. The gateway, detection, masking, dashboard, and provider integrations are scheduled in later milestones.

## Quick start

```bash
git clone https://github.com/kvrishwanth1800-cmd/frostglass.git
cd frostglass
docker compose up --build
curl http://localhost:8000/health
```

The first startup creates strong local values in the ignored `.env.local` file. Do not commit that file. A successful response is:

```json
{"status":"ok","version":"0.0.1"}
```

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export FG_VAULT_ENCRYPTION_KEY="$(python -c 'import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
export FG_TENANT_SALT="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
make test
make lint
make typecheck
```

## Security posture

- Frostglass validates its vault encryption key and tenant salt at startup in every environment.
- Detection is probabilistic and will miss some values.
- Pseudonymization can change model behavior.
- Frostglass supports compliance programs. It does not make an organization compliant.

## License

[Apache-2.0](LICENSE).
