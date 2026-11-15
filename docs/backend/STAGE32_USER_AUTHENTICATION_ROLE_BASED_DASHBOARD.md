# Stage 32 — User Authentication, Secure Login & Role-Based Dashboard

- First-run `/api/auth/register` creates the initial administrator only when the users table is empty.
- `/api/auth/login` verifies PBKDF2-HMAC-SHA256 password hashes (310,000 iterations, per-user random salt) and issues a 12-hour opaque bearer token.
- Only SHA-256 token digests are stored in SQLite.
- `/api/auth/me` returns the current identity; `/api/auth/logout` revokes the session.
- Admin-only `/api/auth/users` endpoints list, create, change role and deactivate accounts.
- Roles: viewer (read), analyst (read/write), admin (read/write plus user administration).
- `TERRASCAN_USER_AUTH_REQUIRED=true` enforces sessions on non-auth API routes.
- A reusable login UI component and typed API helper are supplied. The existing app shell is not yet wired to force login globally.

## Initial setup
On a fresh database, POST `/api/auth/register` with a username and password of at least 12 characters. It succeeds only once and creates the initial administrator.

## Security limitations
Stage 31 API-key auth remains separate and optional. Avoid enabling both gates unless credentials are integrated correctly. This is baseline authentication, not a complete enterprise identity system: HttpOnly cookie/BFF sessions, CSRF controls, MFA, password reset, rate limiting, per-user audit identity and external security review remain future work. Use HTTPS.
