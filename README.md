# TERRASCAN

Planetary Analog Intelligence & Exploration Platform.

## Stage 5 — Scientific Analog Similarity Engine

### Stack
- React, TypeScript, Vite
- MapLibre GL JS
- Earth geographic reference: OpenStreetMap raster tiles
- Moon/Mars browse maps: USGS Astrogeology WMS
- Scientific framework: typed TypeScript evidence, reference and scoring modules
- Planned backend: Python / FastAPI
- Planned science processing: NumPy, Pandas, GeoPandas, Rasterio, Scikit-learn
- Planned database: SQLite

### Run locally
Requires Node.js 20.19+ or 22.12+.

```bash
npm install
npm run typecheck
npm run build
npm run dev
```

## Stage 5 features
- Seven configurable criteria: geology, terrain, thermal, atmosphere, radiation, resources and operations
- Configurable criterion weights with automatic normalization
- Typed scientific evidence and target-reference records
- Source provenance fields: title, organization, URL, dataset ID and access date
- Optional uncertainty, spatial resolution and temporal coverage metadata
- Range, target-value and categorical comparison functions
- Unit compatibility checks
- Separate completeness and confidence indicators
- Separate mission suitability gates
- Aggregate similarity withheld until every required evidence/reference pair is available
- Similarity Engine workspace with Moon/Mars selection and candidate status

## Scoring policy
- Range comparison: 100 inside the reference interval; outside values decay linearly by distance relative to interval width.
- Target-value comparison: linear penalty by relative absolute difference, bounded at zero.
- Categorical comparison: exact normalized category match gives 100; mismatch gives 0.
- Unit mismatch or missing evidence/reference yields no criterion score.
- Aggregate similarity is withheld until all required criteria have compatible evidence and reference records.
- Data completeness is the proportion of required criterion pairs available.
- Confidence is a heuristic from evidence quality and comparability labels; it is not a probability.
- Mission suitability is a separate pass/fail/unknown gate evaluation and is not inferred from similarity.

## Current data state
`src/data/scienceEvidence.ts` intentionally contains empty evidence and target-reference arrays. The initial candidate locations therefore receive 0% data completeness and no similarity or confidence score. This is intentional; no scientific measurements have been invented.

## Important limitations
- Default weights and scoring functions are provisional and require domain-expert review and calibration.
- Unit conversion is not automatic; values must use compatible units before scoring.
- Categorical similarity currently uses exact category matching; richer taxonomies require reviewed mappings.
- Confidence is a transparent heuristic, not a calibrated uncertainty model.
- No backend, database, audit log or evidence upload workflow is implemented yet.
- UI production build has not been verified because dependencies could not be installed in the execution environment. The standalone scientific TypeScript modules passed strict type-checking.

## Next stage
Stage 6: integrate traceable scientific datasets for the seven criteria. Start with terrain/topography, thermal environment and geology. Add ingestion metadata, units/CRS, spatial and temporal coverage, quality flags, uncertainty and reproducible processing records. Do not populate values or compute candidate scores from browse imagery alone.


## Stage 6 — Scientific Dataset Integration

### Catalogued source products
The Stage 6 source catalogue currently includes:
- Lunar LOLA archive and derived DEMs (MIT LOLA PDS node / NASA PDS)
- Mars MOLA MEGDR global topography products (NASA PDS Geosciences Node)
- Mars THEMIS daytime/nighttime global IR mosaics (ASU Mars Space Flight Facility)
- Mars TES thermal inertia products (ASU Mars Space Flight Facility)
- Mars global geology browse/map products (NASA Ames Marsoweb)

These are catalogued discovery entry points, not downloaded or ingested files. Product-specific labels and documentation remain mandatory before processing.

### Ingestion manifest
`src/science/ingestion.ts` defines the required metadata and validation rules:
- Official dataset identifier and source
- Retrieval timestamp and SHA-256 checksum
- File format and product version
- CRS / projection and spatial resolution
- Units and spatial/temporal coverage
- Processing steps, quality flags and uncertainty description

`src/data/ingestionManifests.ts` is intentionally empty until actual files are downloaded and inspected.

### Data integrity
- A browse image or WMS tile is not accepted as a quantitative raster.
- Do not assume a single CRS, unit, resolution or time period for all products.
- MOLA final Version L products use IAU 2000; older versions may use IAU 1991.
- THEMIS day/night mosaics are distinct products and must retain temporal context.
- Lunar south-pole high-resolution DEMs are regional, not global.
- Dataset catalogue status does not imply successful download, ingestion or validation.

### Current implementation scope
Stage 6 adds the source catalogue, metadata inspection UI and ingestion-manifest validator. It does not download source datasets, derive candidate measurements, or change the empty evidence registry. No similarity scores are generated from catalogued products.

## Stage 7 — Validated Raster Ingestion & Evidence Bridge

Stage 7 adds a dependency-free local inspection utility and a science-evidence traceability gate:

- `node scripts/inspect-dataset.mjs <raster-file> [--header <metadata-file>]` calculates SHA-256, records file size/time, parses ENVI headers, detects basic TIFF metadata and captures PDS/XML label previews.
- `src/science/evidenceBridge.ts` checks that a proposed measurement references the same dataset and criterion as its ingestion manifest and catalogue entry.
- Detailed workflow, directory layout, commands and scientific limitations: `docs/data-ingestion/STAGE7_INGESTION_WORKFLOW.md`.

The inspector is first-pass only. Use GDAL/Rasterio and official planetary product tools/labels for authoritative CRS, datum, scale/offset, calibration and uncertainty. No raw planetary products have been downloaded in this stage; the ingestion manifest and evidence registries remain empty and no similarity scores are generated.

## Stage 8 — Controlled Local Ingestion

See [`docs/data-ingestion/STAGE8_CONTROLLED_INGESTION.md`](docs/data-ingestion/STAGE8_CONTROLLED_INGESTION.md) for the Python CLI, HTTPS host allow-list, content-addressed raw storage, optional Rasterio inspection and pending-review manifests. No planetary dataset is presumed downloaded or scientifically validated.


## Stage 9 — Raster Processing & Feature Extraction

See [`docs/data-ingestion/STAGE9_RASTER_PROCESSING.md`](docs/data-ingestion/STAGE9_RASTER_PROCESSING.md) for explicit-grid reprojection, guarded terrain derivatives, and polygon zonal statistics. Derived outputs retain source hashes and provenance; none are treated as validated science evidence automatically.


## Stage 10 — Analog Comparison

See [`docs/data-ingestion/STAGE10_ANALOG_COMPARISON.md`](docs/data-ingestion/STAGE10_ANALOG_COMPARISON.md) for the feature-level Earth–Moon–Mars comparison engine, coverage gates and ranking policy.


## Stage 11 — Interactive Scientific Dashboard

See [`docs/data-ingestion/STAGE11_SCIENTIFIC_DASHBOARD.md`](docs/data-ingestion/STAGE11_SCIENTIFIC_DASHBOARD.md) for the interactive charts, feature coverage, candidate filtering and CSV/JSON report export.

## Stage 12 — Backend & Database

A local FastAPI + SQLite service is included under `backend/`. See [`docs/backend/STAGE12_BACKEND_DATABASE.md`](docs/backend/STAGE12_BACKEND_DATABASE.md) for setup, API endpoints, integrity rules and limitations. Start the service with `cd backend && pip install -r requirements.txt && python run.py`. The database is created empty on first startup.


## Stage 16 — Scientific Reports
Run the FastAPI backend and open the **Scientific Reports** workspace to generate target-specific PDF and CSV exports. See `docs/backend/STAGE16_SCIENTIFIC_REPORTING.md` for endpoints, inclusion rules, limitations and tests. Reports use only approved observations and approved source manifests; comparison scoring is explicitly not computed by this service.


## Stage 17 — Mission Suitability

See [Stage 17 documentation](docs/backend/STAGE17_MISSION_SUITABILITY.md) for mission profile revisions, evidence gates, constraint outcomes, API routes, unit policy and operational limitations. Mission suitability is a constraint-gate assessment and is separate from analog similarity.


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


## Stage 22 — Planetary validation

Run `python scripts/terrascan_validate.py <inspection.json> --expected-body Mars --label <pds4-label.xml>` to generate a conservative metadata validation report. See `docs/backend/STAGE22_PLANETARY_VALIDATION.md`. Reports never approve evidence or modify source data.


### Stage 23 — Advanced spatial analysis
Run `python scripts/terrascan_spatial.py --help` for multiscale raster metrics. A matching Stage 22 validation report and explicit pixel-spacing units are required. See `docs/backend/STAGE23_ADVANCED_GEOGRAPHIC_ANALYSIS.md`.


### Stage 24 — Surface feature classification
Run `python scripts/terrascan_classify.py --help` for deterministic, user-configured terrain classification. A Stage 22 validation report and reviewed class-threshold configuration are required. See `docs/backend/STAGE24_SURFACE_FEATURE_CLASSIFICATION.md`.


### Stage 25 — Planetary analog discovery
Run `python scripts/terrascan_analog_discovery.py --help` to compare approved Moon/Mars target features against approved Earth candidate features. The method is explainable weighted nearest-neighbour retrieval, not a trained ML model. See `docs/backend/STAGE25_ANALOG_DISCOVERY.md`.


## Stage 26 — Supervised terrain pattern recognition
An optional scikit-learn Random Forest workflow is available for operator-supplied labelled terrain samples. Install `requirements-ml.txt`, follow `data/ml-training/README.md`, and see `docs/backend/STAGE26_ML_TERRAIN_PATTERN_RECOGNITION.md`. No trained model or labelled planetary dataset is included; inference is pending human review and does not imply cross-planet generalization.


## Stage 27 — Predictive terrain analysis
An optional group-aware Random Forest regression workflow predicts an explicitly defined continuous target from operator-supplied labelled samples. It reports holdout errors and approximate residual-calibrated intervals. No planetary dataset/model is bundled; predictions remain exploratory and require independent scientific validation. See `docs/backend/STAGE27_PREDICTIVE_TERRAIN_ANALYSIS.md`.


## Stage 28 — Intelligent mission-site ranking
An evidence-gated shortlist combines Stage 25 analog discovery reports and Stage 17 mission-constraint assessments. It withholds incomplete or ineligible sites and applies an explicit operator-defined uncertainty penalty. No real site ranking or authorization is bundled. See `docs/backend/STAGE28_INTELLIGENT_MISSION_SITE_RANKING.md`.


## Stage 29 — Integrated QA
Use `python scripts/terrascan_qa.py project` for project structure and static checks, or `python scripts/terrascan_qa.py integrity path/to/manifest.json` to verify file hashes against a supplied manifest. This is not scientific or security certification. See `docs/backend/STAGE29_INTEGRATED_SCIENTIFIC_QA.md`.

## Stage 30 deployment quick start

Copy `.env.example` to `.env`, edit the allowed frontend origin, then run `docker compose up --build -d api`. The API exposes liveness at `/api/health` and database readiness at `/api/ready`. See `docs/backend/STAGE30_FINAL_INTEGRATION_DEPLOYMENT_RELEASE.md`. This is not a cloud deployment; do not expose the API publicly without authentication and HTTPS/network controls.

## Stage 31 security

Docker Compose now requires `TERRASCAN_API_KEYS` and enables bearer authentication by default. Configure separate high-entropy `read` and `admin` keys in `.env`. Never put admin keys in Vite/frontend variables. See `docs/backend/STAGE31_PRODUCTION_SECURITY_AUTH_ACCESS_CONTROL.md` for security boundaries and browser integration requirements.

## Stage 32 user authentication

Backend account/session endpoints and a reusable login workspace are included. See `docs/backend/STAGE32_USER_AUTHENTICATION_ROLE_BASED_DASHBOARD.md`. The app shell still requires wiring before login is mandatory on every page.

## Final productization stages 33–38

The cumulative release adds the administration workspace, in-memory session lifecycle, authenticated API client, security throttling/headers and release audit. Enable `VITE_USER_AUTH_REQUIRED=true` for the login gate and `TERRASCAN_USER_AUTH_REQUIRED=true` on the API. See `docs/backend/STAGE38_FINAL_RELEASE_VALIDATION.md`.
#   T E R R A S C A N  
 #   T E R R A S C A N  
 