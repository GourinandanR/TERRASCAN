# Stage 20 — Risk Review, Mitigation Verification & Mission Readiness

## Scope
Stage 20 adds append-only human review events for individual risks in a Stage 19 assessment, approved-evidence verification for mitigation closure, and a derived workflow readiness overview.

## API
- `POST /api/mission-risk-assessments/{id}/reviews` — append a reviewer decision.
- `GET /api/mission-risk-assessments/{id}/reviews` — retrieve review history.
- `GET /api/mission-readiness/{id}` — derive current workflow status from the latest review for each risk.

## Review decisions
- `acknowledged`: reviewer records that the risk was reviewed; this does not close the risk.
- `action-required`: outstanding action is explicitly recorded.
- `mitigation-verified`: accepted only when at least one supplied `manifest:<id>` or `observation:<id>` reference resolves to approved evidence. Observation evidence must itself be approved and its source manifest must also be approved.

The service stores a snapshot of the evidence identifier, approval state and manifest SHA-256 at review time. Later review events do not overwrite earlier events. Latest review per risk drives the readiness view.

## Readiness states
- `open-actions`: at least one latest decision is `action-required`.
- `review-incomplete`: at least one risk has no review event.
- `mitigations-not-verified`: all risks have review events, but one or more are acknowledged rather than mitigation-verified.
- `reviewed-mitigations-verified`: every risk's latest review is mitigation-verified with approved evidence references.

These are workflow states only. `operational_authorization` always remains `not-assessed`. The dashboard does not certify mission readiness, determine hazard acceptability, validate the adequacy of evidence content, or grant launch/landing authorization.

## Evidence handling
Only existing approved manifests and approved observations backed by approved manifests may support a `mitigation-verified` decision. References must use the explicit prefixes `manifest:` or `observation:`. The service verifies registry state and captures checksums; a qualified human reviewer remains responsible for deciding whether the underlying evidence actually demonstrates mitigation effectiveness.

## Limitations
No autonomous closure, safety case, risk probability, quantitative risk score, fault-tree analysis, FMEA scoring, reliability prediction, or mission-success prediction is performed. Reviewer identities are self-reported application fields; production authentication and authorization are outside this local prototype.
