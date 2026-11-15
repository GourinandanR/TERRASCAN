# Stage 25 — AI-Powered Planetary Analog Discovery

## What this stage provides
An explainable, deterministic weighted nearest-neighbour retrieval engine that compares an approved Moon/Mars target feature profile with approved Earth analog feature records. It is an AI-assisted discovery workflow, **not a trained machine-learning model**. It does not discover scientific features from imagery; it compares supplied measurements.

## Input contract
Create a JSON file containing:
- `target`: `body` (`Moon` or `Mars`), an optional ID, and a `features` object.
- `featureDefinitions`: unique feature names, explicit units, positive weights and positive absolute tolerances.
- `candidates`: Earth candidate IDs/names and feature objects.

Every feature record requires:
```json
{
  "value": 123.4,
  "unit": "m",
  "status": "approved",
  "manifestStatus": "approved",
  "sourceSha256": "64-character lowercase SHA-256 digest"
}
```
The digest format is checked here; this stage does not reopen source files to re-verify the digest. Approval states must originate from the existing evidence review workflow. Do not manually mark evidence approved unless the established reviewer process has approved it.

## Run
```bash
python scripts/terrascan_analog_discovery.py path/to/approved-analog-input.json
```
Optional output path:
```bash
python scripts/terrascan_analog_discovery.py path/to/approved-analog-input.json --output path/to/report.json
```
Existing output files are never overwritten.

## Scoring
For each required feature:
`normalizedDifference = min(abs(targetValue - candidateValue) / tolerance, 1)`

The overall score is the weighted mean of `1 - normalizedDifference`, expressed from 0 to 100. Feature weights and tolerances are supplied by the operator and must be justified for the data product and scientific question. The score is not a probability, a physical equivalence measure, or a mission-suitability score.

## Eligibility and safeguards
- Target body must be Moon or Mars; candidates must be Earth.
- Every required target and candidate feature must have explicit matching units, approved observation status, approved source-manifest status, finite numeric value and a SHA-256-shaped provenance field.
- Missing, unapproved, malformed or unit-incompatible features withhold candidate ranking.
- Non-Earth candidates are excluded.
- Rankings are pending human review. Evidence approval is unchanged; mission suitability remains not assessed.

## Limitations
No measurements, Earth site feature values, weights, tolerances, model training data or rankings are bundled. The quality of discovery depends entirely on approved input data, feature selection, spatial/temporal representativeness, and scientifically justified tolerances. This method does not model uncertainty or feature covariance.
