# Stage 30 — Final Integration, Deployment & Release

## Runtime configuration
- `TERRASCAN_DB_PATH`: SQLite file path; container default `/app/data/terrascan.sqlite3`.
- `TERRASCAN_CORS_ORIGINS`: comma-separated exact browser origins. Do not use `*` in production.
- `VITE_API_BASE_URL`: frontend build-time API origin.

Copy `.env.example` to `.env`, replace example origins with trusted deployment origins, and never commit `.env`.

## Container startup
From repository root:

```bash
cp .env.example .env
docker compose build api
docker compose up -d api
docker compose ps
```

The API listens on port 8000. SQLite data persists in the `terrascan-data` named volume. Back up the database before upgrades.

## Health checks
- `GET /api/health`: liveness; confirms the API process responds.
- `GET /api/ready`: readiness; verifies SQLite can execute a query; returns HTTP 503 if unavailable.

## Local development
Backend: `cd backend && python -m pip install -r requirements.txt && python run.py`
Frontend: `npm install && npm run dev`; set `VITE_API_BASE_URL=http://127.0.0.1:8000` as needed.

## Verification
Run `npm run qa:project`, `npm run qa:test`, and `cd backend && python -m pytest -q -p no:cacheprovider tests`. A frontend production build requires installed JavaScript dependencies and `npm run build`.

## Operational limitations
This is a deployment package, not a live cloud deployment. SQLite is intended for a single instance with persistent storage; assess a managed database before horizontal scaling or high write concurrency. Authentication/authorization, TLS termination, rate limiting, backup automation, secret-manager integration and security certification are not included. Do not expose the API publicly without HTTPS and access controls. Scientific evidence remains subject to human review; no planetary measurements, model results, rankings or mission authorization are fabricated.
