# Stage 12 — Backend & Database Integration

## Scope

Stage 12 introduces a local FastAPI service and persistent SQLite store. The service stores provenance records and evidence but deliberately does not generate scientific measurements, validate scientific interpretation, or compute similarity scores.

## Architecture

- API: FastAPI + Pydantic v2 (`backend/app/main.py`)
- Persistence: SQLite, foreign keys enabled, WAL journal mode (`backend/app/database.py`)
- Default database: `backend/data/terrascan.sqlite3` (created on first API startup)
- Override: `TERRASCAN_DB_PATH`
- CORS defaults: `http://localhost:5173,http://127.0.0.1:5173`; override with `TERRASCAN_CORS_ORIGINS`
- Frontend client: `src/services/api.ts`; `VITE_API_BASE_URL` configures the API origin

## Start locally

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The API listens on `http://127.0.0.1:8000`. Interactive OpenAPI docs are at `/docs` and health is at `/api/health`.

Frontend (in another terminal, from repository root):

```bash
npm install
npm run dev
```

Optional `.env` in the project root:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API and SQLite health |
| POST / GET | `/api/manifests` | Register/list checksum-bound manifests |
| GET | `/api/manifests/{id}` | Retrieve a manifest |
| POST / GET | `/api/observations` | Register/list scientific observations |
| POST / GET | `/api/target-profiles` | Register/list Moon/Mars reference features |
| POST / GET | `/api/comparison-runs` | Create/list immutable input snapshots for comparison runs |
| GET | `/api/audit` | Recent audit events |

## Integrity and review rules

- Manifest checksums must be exactly 64 hexadecimal characters.
- Manifest source URIs must use HTTPS or a local `file:` URI.
- Numeric evidence and target values must be finite.
- Foreign keys are enforced; observations must reference an existing manifest.
- Observation registration is rejected unless the referenced manifest is explicitly `approved`.
- Duplicate dataset/checksum pairs and duplicate target-body/feature keys are rejected.
- All inserts create audit events.
- Comparison run creation stores a snapshot of the currently stored observations and target references. It is marked `queued`; this API does not calculate results.
- SQLite starts empty. No measurements, target values, or scores are seeded.

## Validation

Run API tests from the backend directory:

```bash
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

The tests use a temporary SQLite database and check health, manifest review gating, and approved-manifest evidence registration.

## Limitations

- This is a local development API, not a production deployment. Authentication, authorization, TLS termination, backups, rate limiting, migrations, and multi-user concurrency policy are not implemented.
- `review_status` is a controlled registration field; an authenticated review workflow and reviewer identity are future work.
- The frontend currently exposes a live health check and typed API client. Existing scientific workspaces remain intact and are not silently populated from the API.
- Comparison runs are snapshots only. The existing evidence-gated TypeScript engine remains responsible for scoring; a future server-side worker must use the same validation rules before persisting results.
