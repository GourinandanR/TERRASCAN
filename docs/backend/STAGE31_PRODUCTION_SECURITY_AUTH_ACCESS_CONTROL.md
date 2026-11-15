# Stage 31 — Production Security, Authentication & Access Control

## API authentication
The API supports static bearer API keys configured through environment variables:
- `TERRASCAN_AUTH_REQUIRED=true` enables authentication.
- `TERRASCAN_API_KEYS` is a comma-separated list of `key:role` entries.
- Keys must be at least 32 characters.
- `read` role permits GET/HEAD requests.
- `admin` role permits GET/HEAD and write requests.
- Missing/invalid credentials are rejected. If authentication is enabled but no keys are configured, API requests fail closed with HTTP 503.
- `/api/health`, `/api/ready`, and CORS preflight OPTIONS are exempt for health probes/browser negotiation.

Generate unique high-entropy keys, for example with Python:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Put the generated values into `.env` as `TERRASCAN_API_KEYS=READ_KEY:read,ADMIN_KEY:admin`. Do not use the example placeholders and do not commit `.env`.

Example request:
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_KEY" http://localhost:8000/api/manifests
```

## Deployment
The Docker Compose configuration enables authentication by default and requires `TERRASCAN_API_KEYS` to be set. Health probes remain unauthenticated. Use exact `TERRASCAN_CORS_ORIGINS` values for trusted frontend origins.

## Frontend integration
The current browser UI does not include a secure API-key entry/session mechanism. Do not place admin keys in Vite environment variables or bundle them into browser JavaScript: Vite variables are public. For browser-based deployment, put the API behind an authenticated backend-for-frontend/reverse proxy or implement a proper user login/session flow before enabling browser writes.

## Security boundaries and remaining work
This is a baseline shared-secret access gate, not a complete identity system. It does not provide user accounts, password login, token expiry/rotation automation, revocation UI, per-user audit identity, CSRF/session management, rate limiting, or fine-grained resource permissions. Static keys are shared credentials; use separate high-entropy keys and rotate them operationally. Deploy only behind HTTPS and network controls. No security certification is claimed.
