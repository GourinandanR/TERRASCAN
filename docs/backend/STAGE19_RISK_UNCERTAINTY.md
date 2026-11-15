# Stage 19 — Mission Risk & Uncertainty Management

## Scope
Stage 19 adds immutable qualitative risk assessment snapshots. Each risk records a user-authored description, category, qualitative likelihood and impact, uncertainty classification and basis, mitigation text, and optional evidence reference identifiers. Assessments may link to a previously saved Stage 18 scenario; target body and site must match.

## API
- `POST /api/mission-risk-assessments` — validate and save an assessment snapshot.
- `GET /api/mission-risk-assessments` — list snapshots.
- `GET /api/mission-risk-assessments/{id}` — retrieve a snapshot.

## Qualitative classification
- `indeterminate`: likelihood, impact or uncertainty is unknown.
- `attention-required`: impact is major/severe and likelihood possible/likely.
- `monitor`: other known qualitative combinations.

This is a transparent triage convention, not a calibrated risk matrix. It does not calculate probability, expected loss, numeric scores, rankings or mission safety. `uncertainty_basis` is mandatory. Evidence references are stored exactly as supplied and are not verified, dereferenced or treated as approved evidence. The UI makes this limitation explicit.

## Immutability and traceability
Every submission creates a new UUID assessment with exact input and result JSON snapshots. Existing assessments are read-only. A linked scenario's input snapshot is copied into the risk snapshot. Creation is audit logged. Changes should be represented by a new assessment, not edits to an old one.

## Limitations
The qualitative categories and triage rule are configurable engineering conventions, not a validated aerospace risk standard. No fault tree, FMEA scoring, hazard probability, severity quantification, Monte Carlo analysis, reliability model, causal inference or safety certification is performed. User-provided evidence identifiers are not automatically validated against the evidence registry. Risk review and mitigation closure remain human responsibilities.
