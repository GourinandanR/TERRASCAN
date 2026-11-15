# Stage 17 — Mission-Constraint & Operational Suitability

## Purpose and separation from similarity

Mission suitability is a constraint-gate assessment, not an Earth–Moon–Mars analog similarity score. Similarity describes resemblance under selected environmental features; it does not establish landing safety, engineering compliance, or mission authorization. This API does not compute a weighted score, rank sites, or certify a site.

## Profile model

A mission profile is stored as an immutable `(id, revision)` record. Creating another profile with the same supplied ID creates the next revision; previous revisions remain addressable. Each criterion has:

- `key`: exact observation criterion identifier
- `unit`: expected unit string
- `minimum` / `maximum`: optional inclusive numeric bounds
- `required`: whether missing evidence blocks eligibility
- `description`: human-readable purpose

All new profiles are `user-configured-unvalidated`. The API does not seed numerical mission limits, and callers cannot mark a profile scientifically validated through this endpoint. Thresholds must be independently justified from mission requirements and authoritative engineering/science references before operational use.

## Assessment decision logic

Each criterion returns one of `pass`, `fail`, `unknown`, or `not-applicable`.

- A required criterion with no approved evidence is `unknown`.
- Evidence is eligible for evaluation only when both its observation and source manifest are approved.
- Unit matching is exact apart from letter case and surrounding whitespace. No implicit conversion is performed. A mismatch yields `unknown`.
- Configured bounds are inclusive. A measurement exactly on a bound passes; a value outside either bound fails.
- Optional criteria with no evidence are `not-applicable` and do not block eligibility.
- Any failed required criterion makes the overall assessment `ineligible`.
- Otherwise, any unknown required criterion makes it `indeterminate`.
- Only when all required criteria pass does the assessment return `eligible`.

A missing or rejected observation is never treated as a pass. A rejected record remains retained in the evidence system but is excluded from the assessment snapshot.

## Evidence and snapshot provenance

New manifests must enter pending review; callers cannot self-approve a manifest by setting its creation status. Approval must be recorded through the audited review endpoint. Every assessment stores an immutable input snapshot containing the exact profile ID/revision, configured criteria, target body, site ID, and approved observations joined to their approved source manifest. The snapshot includes manifest checksum, dataset identifier/version and source URI. The result and snapshot are persisted together; later profile revisions or review decisions do not rewrite historical assessments.

## Units, coordinate frames and measurement semantics

The current evaluator deliberately does not convert units. For example, `deg` and `degree` are not assumed equivalent; `m` and `cm` are not converted. Configure criterion units to match the canonical units of approved observations or add an independently tested conversion layer in a later stage. Unit equality alone does not guarantee semantic comparability: confirm datum, coordinate reference system, vertical reference, spatial resolution, temporal coverage, instrument calibration, uncertainty, aggregation method and observation footprint before approving evidence.

The API currently compares scalar values by criterion key. It does not interpret slope distributions, roughness algorithms, thermal temporal envelopes, radiation spectra/dose periods, resource accessibility, communication geometry, power/energy, trafficability, hazard maps, or landing dispersion models. Such multidimensional constraints need explicit schemas and validated algorithms before being represented as scalar limits.

## API

- `POST /api/mission-profiles` — create an immutable profile revision.
- `GET /api/mission-profiles` — list profile revisions.
- `POST /api/suitability-assessments` — assess one site against an exact profile revision.
- `GET /api/suitability-assessments` — list assessment snapshots/results.
- `GET /api/suitability-assessments/{id}` — retrieve an immutable assessment.

## Safety and limitations

This is a research workflow implementation, not a flight rule system. An `eligible` result only means the available approved scalar evidence satisfied every required configured bound. It must not be interpreted as safe to land, crew-safe, resource-proven, reachable, or mission-authorized. Profiles are unvalidated by default; no real planetary measurements are seeded. Earth observations should not be assumed transferable to Moon/Mars without a separately justified analog model.
