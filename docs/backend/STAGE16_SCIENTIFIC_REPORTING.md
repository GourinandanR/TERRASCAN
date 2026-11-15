# Stage 16 — Scientific Reporting & Export Engine

## Purpose
Generate reproducible PDF and CSV exports from the persistent Stage 12 database. Reports are scoped to a Moon or Mars target and summarize approved Earth observations, approved dataset manifests, target reference records and review-queue counts.

## Endpoints
- `GET /api/reports/{Moon|Mars}/summary` — JSON report data for the UI.
- `GET /api/reports/{Moon|Mars}/csv` — CSV evidence table.
- `GET /api/reports/{Moon|Mars}/pdf` — formatted PDF report.

## Inclusion rules
- Earth observations are included only when both the observation and its source manifest have `approved` review status.
- Only approved source manifests appear in the approved-manifest provenance section.
- Target references are included exactly as stored for the selected target.
- Pending/rejected counts are reported separately.
- Values, units, quality labels, reviewer details and source SHA-256 values are not recalculated or normalized by the reporting layer.

## Interpretation and limitations
- The report service does not calculate similarity scores, rankings, confidence, or mission suitability.
- The report explicitly labels comparison status as `not-computed`.
- Missing observations and references remain absent; no placeholder scientific values are inserted.
- Report approval state reflects workflow decisions, not a guarantee of scientific correctness.
- Review source product documentation for coordinate frame, datum, units, temporal coverage, uncertainty, calibration and processing methodology.

## Run
Install backend requirements:
```bash
cd backend
pip install -r requirements.txt
python run.py
```
Open the frontend, choose **Scientific Reports**, select Moon or Mars, and download PDF or CSV. The backend must be running.

## Test
```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q tests/test_api.py
```
Stage 16 tests verify summary contents, CSV headers/content type and PDF signature/download headers. The tests use temporary SQLite storage and do not add real scientific data.
