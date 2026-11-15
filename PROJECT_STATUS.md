# TERRASCAN — Project Status

## Current stage
Stage 29 — Integrated Scientific Validation & System QA

## Architecture
- Frontend: React, TypeScript, Vite, Tailwind CSS
- Mapping: MapLibre GL JS
- Earth reference: OpenStreetMap raster tiles
- Moon/Mars browse maps: USGS Astrogeology WMS
- Scientific framework: typed evidence, reference, scoring and ingestion modules
- Planned backend: Python / FastAPI
- Planned science processing: NumPy, Pandas, GeoPandas, Rasterio, GDAL
- Planned database: SQLite

## Completed
- [x] Stage 1 architecture approved
- [x] Stage 2 frontend foundation
- [x] Stage 3 interactive Earth map and candidate locators
- [x] Stage 4 Earth/Moon/Mars Planetary Explorer
- [x] Stage 5 evidence-gated similarity framework
- [x] Stage 6 scientific dataset source catalogue
- [x] Lunar LOLA archive / derived DEM entry
- [x] Mars MOLA MEGDR topography entry
- [x] Mars THEMIS day/night IR mosaic entries
- [x] Mars TES thermal inertia entry
- [x] Mars global geology map entry
- [x] Dataset metadata inspection UI with target and criterion filters
- [x] Ingestion manifest type and validation function
- [x] Required provenance, checksum, CRS, units, coverage, quality and uncertainty fields
- [x] Empty ingestion manifest registry pending actual product downloads
- [x] Stage 7 local SHA-256 and first-pass raster/label inspector (Node.js built-ins)
- [x] ENVI header metadata extraction
- [x] Basic classic TIFF dimension/sample metadata extraction
- [x] PDS/XML label preview preservation
- [x] Evidence-to-manifest-to-catalogue traceability validator
- [x] Stage 7 reproducible workflow documentation
- [x] Stage 8 Python controlled-ingestion CLI (`download`, `inspect`, `manifest`)
- [x] HTTPS-only download and per-dataset host allow-list
- [x] Same-host redirect enforcement and configurable download size limit
- [x] Streaming SHA-256 and optional expected-checksum verification
- [x] Content-addressed raw storage with overwrite refusal
- [x] Optional Rasterio metadata, CRS, transform, bounds, resolution and band inspection
- [x] Checksum-bound provenance manifest creation, always pending human review
- [x] Explicit review gates for CRS, units, footprint, time, quality and uncertainty
- [x] Stage 8 setup and operating documentation

## Catalogued sources and limitations
1. Moon LOLA — MIT LOLA PDS node and NASA PDS. Archive includes EDR/RDR/GDR and derived products; global cylindrical and polar stereographic products exist at several resolutions. A 5 m/pixel DEM is regional to 87–90°S and is not global.
2. Mars MOLA MEGDR — NASA PDS Geosciences Node. Global products include 4, 16, 32, 64 and 128 pixels/degree, with polar products at 128, 256 and 512 pixels/degree. Final Version L products use IAU 2000; older products may use IAU 1991. Product files include labels and ENVI headers.
3. Mars THEMIS — ASU Mars Space Flight Facility. Day and night global mosaics listed at 100 m / 593 pixels per degree and 230 m / 256 pixels per degree.
4. Mars TES thermal inertia — ASU catalogue includes global products at 7.5 km and 3 km scales. Thermal inertia is a derived property, not direct surface temperature.
5. Mars global geology — NASA Ames Marsoweb browse products. The archive describes geology maps composited with MOLA shaded relief for orientation; quantitative use requires original georeferenced data and map documentation.

## Current data state
- Dataset catalogue: 5 entries.
- Downloaded files: 0.
- Ingestion manifests: 0.
- Validated products: 0.
- Scientific evidence registry: still empty.
- No candidate measurements or similarity scores have been fabricated.

## Validation
- Catalogue and manifest validator implemented.
- Full frontend typecheck/build not completed because npm dependencies could not be installed in the execution environment.
- Dataset product metadata must be verified from each actual product label before ingestion.

## Stage 7 — implementation delivered
- Added `scripts/inspect-dataset.mjs` for local file hashing and first-pass ENVI/TIFF/PDS-label inspection.
- Added `src/science/evidenceBridge.ts` to validate traceability between measurement, manifest and catalogue record.
- Added `docs/data-ingestion/STAGE7_INGESTION_WORKFLOW.md` with commands, directory layout, review gates and limitations.
- Updated Dataset Integration UI to expose the Stage 7 workflow.

## Current data state after Stage 7
- Downloaded planetary files: 0.
- Ingestion manifests: 0.
- Validated products: 0.
- Scientific evidence records: 0.
- Similarity scores remain withheld.

## Next stage
Stage 8: build a local data store and controlled download/processing workflow for selected LOLA, MOLA and THEMIS/TES products. Add GDAL/Rasterio-backed inspection, immutable raw-file handling, derived-product manifests, spatial footprint checks and human-reviewed unit/CRS validation. Only populate the evidence registry after actual products and their official labels pass these checks.


## Stage 8 — implementation delivered
- Added `scripts/terrascan_ingest.py` with controlled `download`, `inspect` and `manifest` commands.
- Added `requirements-geo.txt` for optional Rasterio inspection.
- Raw downloads use `data/raw/<dataset-id>/<sha256>/`; files are not overwritten.
- Downloads require HTTPS and a dataset-specific allow-listed host; cross-host redirects are rejected.
- Inspection re-hashes the source and optionally extracts Rasterio metadata. It does not infer scientific units or planetary CRS correctness.
- Manifest creation re-checks the source digest and marks every generated manifest `pending-human-review`.
- Added `docs/data-ingestion/STAGE8_CONTROLLED_INGESTION.md` and data directories for raw, inspection, manifests and derived products.

## Current data state after Stage 8
- Downloaded planetary files: 0 (no direct product URL supplied or fetched).
- Inspection reports: 0.
- Ingestion manifests: 0.
- Validated products: 0.
- Scientific evidence records: 0.
- Similarity scores remain withheld.

## Stage 8 validation
- Python syntax compilation and CLI help checks passed.
- Synthetic local fixture completed checksum, inspection and pending-manifest generation.
- Rasterio availability is optional; full raster metadata extraction requires installing `requirements-geo.txt` in a compatible Python/GDAL environment.
- No real planetary product was used for testing.


## Stage 9 — implementation delivered
- Added `scripts/terrascan_process.py` with `grid`, `terrain`, and `zonal` commands.
- Explicit CRS and target resolution are required for common-grid reprojection.
- Slope/aspect derivation is guarded to projected metre CRSs and elevation values explicitly in metres.
- Polygon zonal statistics require an explicit zone CRS that matches the raster CRS.
- Every output includes provenance and SHA-256 hashes of source data.
- Derived rasters and statistics are kept separate from immutable raw inputs.
- Added `docs/data-ingestion/STAGE9_RASTER_PROCESSING.md`.
- Updated project version to 0.9.0 and added npm convenience scripts.

## Stage 9 validation and data state
- Python syntax compilation and CLI help checks are run at packaging time.
- A synthetic GeoTIFF test is attempted only when Rasterio is installed.
- No real planetary raster was processed.
- No validated site feature measurements were added to the Stage 5 evidence registry.
- Similarity scores remain withheld until real source products pass metadata review.


### Stage 9 synthetic validation detail
- `python -m py_compile scripts/terrascan_process.py`: passed.
- CLI help: passed.
- Synthetic GeoTIFF common-grid reprojection: passed.
- Synthetic metre DEM slope/aspect generation: passed.
- Synthetic GeoJSON polygon zonal statistics: passed.
- These are software-path tests only; they do not validate planetary product interpretation or scientific correctness.


## Stage 10 — implementation delivered
- Added typed Earth analog feature observations and Moon/Mars target feature references.
- Added five feature dimensions: slope, roughness, thermal environment, elevation range and geology.
- Added feature-level validation statuses and unit compatibility checks.
- Aggregate scores and rankings require all five feature pairs to be present and compatible.
- Coverage, confidence and similarity are kept separate; confidence is a quality heuristic, not a probability.
- Added `Analog Comparison` navigation workspace and documentation.
- Project version updated to 1.0.0.

## Stage 10 data state
- Earth feature observations: 0.
- Moon/Mars target feature references: 0.
- Candidate rankings issued: 0.
- No actual planetary or Earth site data was fabricated or added.


### Stage 10 validation detail
- Isolated strict TypeScript compilation of `analogComparison.ts` and its candidate-site dependency: passed.
- Synthetic engine tests: passed for empty-data withholding, complete exact-match ranking, and partial-data score/rank withholding.
- Test fixtures were temporary and removed from the deliverable.
- Full React application build remains unverified because frontend dependencies are not installed in this environment.


## Stage 11 — implementation delivered
- Added interactive Scientific Comparison Dashboard using the existing Stage 10 scoring engine.
- Added Moon/Mars target selection, candidate selection and ranking-status filtering.
- Added similarity ranking chart with an honest no-data state.
- Added feature coverage chart, candidate status list and feature-level detail panel.
- Added CSV and JSON export with source registry state, missing statuses, weights and timestamps.
- Added responsive dashboard styling and Stage 11 documentation.
- Project version updated to 1.1.0.

## Stage 11 data and validation state
- Observation registry: 0 records.
- Target feature registry: 0 records.
- Rankings: 0.
- Charts show missing data rather than fabricated examples.
- Frontend build not run because dependencies are not installed in this environment.


## Stage 12 — implementation delivered
- Added FastAPI service with health, manifest, observation, target-profile, comparison-run and audit endpoints.
- Added SQLite schema with foreign keys, WAL mode, indexes and audit event records.
- Added checksum, URL scheme, finite numeric value, enum and payload validation.
- Added evidence registration gate requiring an approved source manifest.
- Added comparison-run input snapshots; API does not fabricate or calculate scientific scores.
- Added typed frontend API client and a Backend & Database workspace with live health status.
- Added environment configuration, setup documentation and API tests.
- Project version updated to 1.2.0.

## Stage 12 validation and data state
- Python compilation: passed.
- FastAPI/SQLite API tests: 5 passed.
- Tests cover health, pending-review evidence rejection, approved-manifest evidence insertion, target profile snapshotting and checksum validation.
- Database remains empty in the delivered project; tests use a temporary database.
- Frontend build/typecheck remains unverified because npm dependencies are not installed in this environment.
- Local development API only; authentication, production deployment hardening, schema migrations and background scoring workers remain future work.

## Stage 13 — Automated Scientific Data Pipeline (v1.3.0)

- Added `scripts/terrascan_pipeline.py` to batch file validation, SHA-256 verification, inspection, provenance manifest creation, optional Stage 12 API synchronization, and run reporting.
- Added an empty pipeline job template at `data/pipeline/jobs.example.json`; no datasets or observations were fabricated.
- Added path traversal protection, controlled dataset IDs, manifest idempotency checks, per-job error reporting, and explicit opt-in API synchronization.
- Manifests remain `pending-human-review`; the pipeline does not auto-approve evidence or calculate similarity scores.
- Added pipeline safety tests and Stage 13 documentation.


## Stage 14 — implementation delivered
- Added `scripts/terrascan_features.py` for polygon-based Earth analog candidate feature extraction from aligned DEM, slope, thermal and categorical geology rasters.
- Added slope distribution statistics, local DEM standard-deviation roughness proxy, thermal statistics, elevation range and dominant geology class with class counts.
- Added strict CRS/grid/unit/site-ID/class-legend validation and SHA-256 provenance for every input.
- Added explicit review-state output (`pending-human-review`); no automatic evidence registration, target profiles, similarity scores or mission suitability.
- Added synthetic raster extraction test and Stage 14 operating documentation.
- Project version updated to 1.4.0.

## Stage 14 validation and data state
- Synthetic aligned-raster feature extraction test: passed.
- Test verified expected slope/thermal values, mapped geology class, elevation range, source provenance and pending-review status.
- No real raster dataset was processed; no scientific evidence or comparison scores were created.
- Full frontend build remains unverified because frontend dependencies are not installed in this environment.

## Next stage
Stage 15: Scientific Evidence Review & Quality-Control Workspace — human review of extracted feature records, explicit approval/rejection reasons, and controlled submission of approved evidence to the Stage 12 API.

## Stage 15 — implementation delivered
- Added human review endpoints for dataset manifests and individual scientific observations.
- Added append-only review decision history with reviewer identity, reason and timestamp.
- Added observation review status and metadata using backward-compatible SQLite startup migration.
- Added pending review queue and review-history APIs.
- Comparison-run snapshots now include only approved observations.
- Added Evidence Review frontend workspace with reviewer identification, mandatory rationale and approve/reject controls.
- Added Stage 15 backend/API documentation and test coverage.
- Project version updated to 1.5.0.

## Stage 15 validation and data state
- Backend API tests: 9 passed.
- Python compilation: passed.
- Stage 13 pipeline and Stage 14 geospatial unit tests: 6 passed.
- No real scientific evidence was created or approved.
- Existing observations migrate to pending-human-review; no automatic approval.
- Full frontend build remains unverified unless dependencies are installed.

## Stage 16 — implementation delivered
- Added evidence-backed JSON report summaries for Moon and Mars targets.
- Added downloadable PDF and CSV report endpoints.
- PDF reports include executive summary, approved observations, target references, source provenance, SHA-256 checksums, review-queue counts and scientific limitations.
- CSV exports include observation values, units, quality, reviewer decision metadata and source manifest identifiers.
- Reports include only observations with approved status and approved source manifests.
- Explicitly labels comparison state `not-computed`; no similarity score, rank or mission suitability is generated.
- Added Scientific Reports frontend workspace with target selector, live summary and PDF/CSV export actions.
- Added Stage 16 documentation and API tests.
- Project version updated to 1.6.0.

## Stage 16 validation and data state
- Backend API tests: 11 passed, including PDF and CSV export checks.
- Stage 13/14 pipeline and geospatial tests: 6 passed.
- Python compilation: passed for backend and report modules.
- No real scientific measurements were added or inferred.
- Full frontend build remains unverified because frontend dependencies are not installed in this environment.

## Next stage
Stage 17: Mission-Constraint & Operational Suitability Assessment — separately model mission constraints and evidence gates; do not equate environmental similarity with mission suitability.

## Stage 17 — Mission-Constraint & Operational Suitability Assessment (v1.7.0)

- Added immutable mission profile revisions with typed criteria, units, optional/required flags and explicit inclusive minimum/maximum bounds.
- Profiles are always created as `user-configured-unvalidated`; no numerical mission thresholds or example operational limits are preloaded.
- Added constraint outcomes: `pass`, `fail`, `unknown`, and `not-applicable`.
- Added fail-closed overall outcomes: `eligible`, `ineligible`, and `indeterminate`.
- Required missing evidence and unit mismatches remain unknown; no implicit unit conversion is performed.
- New manifests cannot self-approve at creation; approval requires the audited human review endpoint.
- Only approved observations joined to approved source manifests enter assessment snapshots.
- Assessment runs persist immutable profile revision, evidence, manifest hashes and provenance, plus the evaluated result.
- Added Mission Suitability workspace for profile JSON editing, profile revision selection and assessment history.
- Added Stage 17 scientific limitations, unit handling, reference-frame cautions and API documentation.
- Project version updated to 1.7.0.

## Stage 17 validation and data state
- Backend API tests: 16 passed, including missing-evidence indeterminate state, inclusive boundary pass, failed constraint ineligibility, unit mismatch, unapproved evidence exclusion, immutable profile revisions and assessment snapshots.
- Existing Stage 13 pipeline and Stage 14 geospatial tests are rerun as part of final validation.
- No real measurements, validated mission thresholds, suitability rankings or mission certifications were added.
- Full frontend build remains unverified if npm dependencies are unavailable in the environment.


## Stage 18 — Mission Planning & Scenario Simulation (v1.8.0)
- Added deterministic DAG-based earliest-start scheduler with cycle and dependency validation.
- Added immutable mission scenario snapshots and list/detail API endpoints.
- Added optional Stage 17 suitability linkage with site/body consistency checks and explicit suitability gate state.
- Added per-activity resource capacity checks; missing capacity remains unknown and exceeded capacity is reported.
- Added Mission Scenarios frontend workspace with editable JSON scenario input and schedule display.
- Added API tests for scheduling, resource constraints, immutable snapshots, dependency cycles, unknown dependencies and suitability mismatch.
- Limitations: no resource leveling, cumulative resource inventory, stochastic simulation, mission predictions or operational authorization.


## Stage 19 — Mission Risk & Uncertainty Management (v1.9.0)
- Added qualitative risk register fields for hazard description, category, likelihood, impact, uncertainty classification and basis, mitigation, and optional evidence references.
- Added deterministic qualitative states: `indeterminate`, `attention-required`, and `monitor`; no probabilities, numeric scores, expected losses or rankings are computed.
- Added optional Stage 18 scenario linkage with target-body and site consistency checks.
- Added immutable assessment input/result snapshots and audit events, with list and detail endpoints.
- Added Mission Risk frontend workspace and explicit limitations on evidence-reference verification.
- Added Stage 19 documentation and API tests.
- Project version updated to 1.9.0.
- No real hazard measurements, calibrated probabilities, or mission safety conclusions were introduced.


## Stage 20 — Risk Review, Mitigation Verification & Mission Readiness (v2.0.0)
- Added append-only human review events for each risk in a Stage 19 assessment.
- Added review decisions: acknowledged, action-required and mitigation-verified.
- Mitigation verification requires at least one approved manifest or approved observation whose source manifest is also approved.
- Review records snapshot the referenced evidence identifiers, approval states and SHA-256 hashes.
- Added risk review history and a derived mission-readiness workflow endpoint.
- Readiness states expose open actions, incomplete reviews, unverified mitigations or fully reviewed/verified mitigations.
- Operational authorization remains `not-assessed` in every state; no mission authorization or safety certification is generated.
- Added Stage 20 frontend review controls, evidence reference input and readiness overview.
- Added Stage 20 documentation and API tests.
- Project version updated to 2.0.0.


## Stage 21 — NASA PDS Discovery & Scientific Data Acquisition (v2.1.0)
- Added `scripts/terrascan_pds.py` for NASA PDS Search API keyword/query searches and logical identifier resolution.
- Search and resolution responses are retained as immutable JSON metadata snapshots with retrieval timestamps, request URLs and SHA-256 digests.
- Preserves the complete API response alongside convenience-normalized product identifiers and titles.
- Added selected XML/PDS4-like label extraction to the existing ingestion inspection report; extracted fields remain unvalidated hints.
- Extended the LOLA and MOLA HTTPS allow-lists to include the official PDS host while retaining same-host redirect enforcement.
- Added Dataset Integration workspace instructions and PDS documentation links.
- Added offline tests for PDS response normalization, snapshot hashes, label extraction and existing pipeline behavior.
- No PDS search results or planetary measurements were automatically imported, downloaded, approved or scored.
- Project version updated to 2.1.0.


## Stage 22 — Planetary Raster Intelligence & Scientific Data Validation (v2.2.0)
- Added `scripts/terrascan_validate.py` to generate immutable, non-overwriting validation reports from Stage 8 inspection JSON and optional PDS XML labels.
- Checks declared target body, raster dimensions, resolution, bounds, CRS presence, common Earth-CRS misuse on Moon/Mars, units and no-data metadata.
- Parses selected PDS XML target/frame/unit hints; missing metadata remains unknown and is never inferred from pixel values.
- Explicitly distinguishes `fail`, `review-required`, and limited `checks-passed`; reports remain `scientificDisposition: not-approved` and do not change evidence approval.
- No reprojection, unit conversion, raster edits, pixel-level quality analysis, or scientific certification is performed.
- Added offline tests and Stage 22 documentation. Project version updated to 2.2.0.


## Stage 23 — Advanced Planetary Geospatial Analysis (v2.3.0)
- Added `scripts/terrascan_spatial.py` for multiscale descriptive raster analysis after Stage 22 validation.
- Computes valid-pixel value distributions, topographic position index, local elevation standard deviation and a terrain-ruggedness proxy at explicitly selected odd-sized neighborhood windows.
- Requires a Stage 22 validation report for the same planetary body and blocks any report containing failed checks; unknown checks remain visible in the report.
- Requires explicit pixel-spacing units from authoritative product documentation; no unit inference or coordinate transformation is performed.
- Binds immutable analysis reports to source raster and validation-report SHA-256 hashes.
- Analysis is descriptive-only; evidence approval remains unchanged and similarity scores are not computed.
- Added synthetic offline tests and Stage 23 operating documentation.
- No real planetary raster was analysed and no scientific measurements or rankings were added.
- Project version updated to 2.3.0.


## Stage 24 — Planetary Surface Feature Extraction & Classification (v2.4.0)
- Added `scripts/terrascan_classify.py`, a transparent deterministic rule engine for slope, topographic position and local elevation variability.
- Class definitions and all thresholds are supplied by the operator in a versioned JSON configuration; no fabricated default scientific classes or thresholds are included.
- Requires a matching Stage 22 validation report and blocks classification when any validation check fails.
- Produces UInt16 class rasters and immutable reports bound to source, validation, configuration and output SHA-256 hashes.
- Explicit metric horizontal and vertical units are required; geographic-degree grids are rejected for slope computation.
- Class outputs remain exploratory and pending human review; evidence approval is unchanged and similarity scores are not computed.
- Added Stage 24 documentation, CLI scripts and offline synthetic tests.
- No real planetary measurements, training datasets, model accuracy claims or site rankings were added.
- Project version updated to 2.4.0.


## Stage 25 — Planetary Analog Discovery (v2.5.0)
- Added `scripts/terrascan_analog_discovery.py`, an explainable deterministic weighted nearest-neighbour engine for approved Moon/Mars target features and Earth analog candidates.
- Feature definitions require explicit units, positive weights and feature-specific tolerances.
- Candidate rankings require complete, unit-compatible target and candidate features with approved observation and source-manifest states plus SHA-256-shaped provenance fields.
- Missing or unapproved features withhold ranking; non-Earth candidates are excluded.
- Reports explain per-feature differences and weighted contributions, scoring formula, limitations and provenance of the input JSON.
- Evidence approval remains unchanged; mission suitability remains not assessed.
- Added Stage 25 tests, docs, npm commands and an empty input workspace.
- No feature measurements, training data, model accuracy claims, site rankings or mission decisions are fabricated.
- Project version updated to 2.5.0.


## Stage 26 — Machine Learning-Based Terrain Pattern Recognition
- [x] Optional supervised Random Forest training and inference CLI (`scripts/terrascan_ml.py`)
- [x] Explicit feature schema, class labels, label basis and per-sample source SHA-256 requirements
- [x] Stratified holdout evaluation with accuracy, confusion matrix and class-wise precision/recall/F1
- [x] Model and training dataset SHA-256 recorded in evaluation output
- [x] Strict inference feature-name/order matching and pending-human-review predictions
- [x] Empty, malformed, insufficient and unprovenanced datasets fail closed
- [x] Optional ML dependency file (`requirements-ml.txt`) and empty training-data workspace
- [x] Stage 26 documentation, frontend workflow instructions and offline software tests
- [ ] Real labelled training corpus, spatially independent validation and cross-body/cross-sensor validation (not supplied; required before scientific use)

**Limitations:** No model is trained in this release because no approved labelled planetary training data was supplied. Synthetic fixtures are used only to test software behavior. Model predictions do not approve evidence, rank sites, assess mission suitability or authorize operations.


## Stage 27 — Predictive Terrain Analysis
- [x] Optional supervised Random Forest regression workflow (`scripts/terrascan_predict.py`)
- [x] Explicit continuous target name/unit and feature schema
- [x] Provenance-backed labelled records with source SHA-256 and target basis
- [x] Spatial-group-aware train/calibration/test separation to reduce spatial leakage
- [x] MAE, RMSE, R², residual summaries and group split metadata
- [x] Residual-calibrated prediction intervals with empirical test coverage reporting
- [x] Model/dataset hashes, strict inference schema and pending-human-review outputs
- [x] Empty predictive-data workspace, docs, frontend instructions and software tests
- [ ] Real labelled planetary target dataset, independent spatial validation and cross-body/cross-sensor validation (not supplied)

**Limitations:** No predictive model is trained in this release because no reviewed planetary target dataset was supplied. Synthetic samples are software-test fixtures only. Prediction intervals are approximate, not guarantees. No physical simulation, site ranking, evidence approval or mission authorization is performed.


## Stage 28 — Intelligent Mission-Site Ranking
- [x] Explainable site-ranking CLI integrating Stage 25 analog reports and Stage 17 suitability snapshots
- [x] Strict site-ID matching, approved-evidence presence and eligible-suitability gates
- [x] Withheld-site reasons for missing, invalid or unapproved prerequisites
- [x] Explicit operator-supplied uncertainty penalty and configurable ranking weights
- [x] Deterministic ranking and tie-break rules
- [x] SHA-256 binding of analog and suitability input reports
- [x] Human-review disposition, no automatic approval or mission authorization
- [x] Empty input workspace, documentation, frontend instructions and offline tests
- [ ] Reviewed real candidate inputs, validated uncertainty basis and independent mission-team review (not supplied)

**Limitations:** No real site rankings are generated because no approved planetary evidence or mission suitability snapshots were supplied. Composite ranking is policy-dependent decision support, not a scientific probability, landing-safety certification or operational decision.


## Stage 29 — Integrated Scientific Validation & System QA
- [x] Project-wide structural audit for required scripts, backend modules, docs and frontend workspace sections
- [x] Package version and CLI script registration checks
- [x] Backend route presence checks for mission profiles, suitability assessments and reports
- [x] Python source syntax audit without generating bytecode
- [x] Regression test file presence audit
- [x] Selected ranking safety-gate static checks
- [x] Artifact manifest SHA-256 integrity verifier with tamper/missing-file detection
- [x] QA documentation, output workspace, frontend workflow and automated tests
- [ ] Scientific validation against reviewed planetary reference datasets and independent domain-expert sign-off (not supplied)
- [ ] Frontend end-to-end/browser tests and security certification (not performed)

**Limitations:** Stage 29 validates project structure and file integrity. It does not certify scientific correctness, geospatial accuracy, model generalization, application security, UI behavior or mission readiness.

## Stage 30 — Final Integration, Deployment & Release
- [x] Containerized API runtime with non-root execution and health check
- [x] Docker Compose deployment with persistent SQLite volume
- [x] Environment templates for database, CORS and frontend API URL
- [x] Liveness and database readiness endpoints
- [x] Unified frontend API base URL for legacy workspaces
- [x] Release documentation and deployment limitations
- [x] Backend release endpoint regression tests
- [ ] Live cloud deployment, production security review, authentication, TLS/reverse-proxy configuration and backup recovery drill (not performed)
- [ ] Frontend production build/browser E2E verification (not performed)

**Limitations:** This is a repeatable container deployment package, not a cloud deployment or public-production security certification. The API has no authentication/authorization layer; do not expose it publicly without additional controls.

## Stage 31 — Production Security, Authentication & Access Control
- [x] Optional bearer API-key authentication middleware
- [x] Read-only and admin roles with write-method restriction
- [x] Constant-time key comparisons and minimum key length validation
- [x] Fail-closed behavior when authentication is enabled without keys
- [x] Public liveness/readiness probes and CORS preflight handling
- [x] Docker Compose enables authentication and requires configured keys
- [x] Security tests and operational documentation
- [ ] Browser login/session integration, per-user identity, key rotation/revocation workflow, rate limiting, TLS deployment and external security review (not included)

**Important:** Do not embed admin API keys in frontend/Vite variables. The existing frontend has no secure login/session flow; browser deployment needs an authenticated backend-for-frontend or a proper user authentication layer before write operations are exposed.

## Stage 32 — User Authentication, Secure Login & Role-Based Dashboard
- [x] PBKDF2 password hashing with per-user salts
- [x] Opaque 12-hour bearer sessions; only token hashes stored
- [x] First-run-only administrator registration
- [x] Login, current-user, logout and session revocation endpoints
- [x] Admin user provisioning, role changes and deactivation
- [x] Optional user-session enforcement middleware
- [x] Reusable frontend login workspace and API helpers
- [ ] Full app-shell integration, HttpOnly cookie/BFF flow, CSRF, MFA, rate limiting and external security review

**Limitations:** Login is supplied as a reusable component; mandatory login is not integrated into every frontend route. This is not a complete enterprise identity system.

## Stages 33–38 — Final Productization (proposed roadmap completed)
- [x] Stage 33: Admin workspace with account listing, provisioning, role changes and deactivation; Administration navigation route.
- [x] Stage 34: In-memory session lifecycle and 30-minute idle timeout; sign-out clears token state.
- [x] Stage 35: Central API client bearer-token injection; CORS allows authenticated PATCH; Docker Compose selects user-session auth instead of requiring two credentials.
- [x] Stage 36: End-to-end API workflow regression coverage for initial admin, account creation, role restriction, logout and registration closure.
- [x] Stage 37: Login/register request throttling and API security response headers.
- [x] Stage 38: Release audit script, final release validation guide and version 3.8.0.
- [ ] Browser-driven E2E, full production identity hardening (HttpOnly/BFF, MFA, password reset), TLS deployment and external penetration testing remain outside this release.

**Limitations:** User login is enforced in the UI only when `VITE_USER_AUTH_REQUIRED=true`; backend enforcement is separately controlled by `TERRASCAN_USER_AUTH_REQUIRED=true`. These must be configured consistently. This is not a security certification.
