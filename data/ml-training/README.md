# Supervised ML training data workspace

No training samples are supplied. Create an operator-reviewed JSON file using the schema below; do not treat example/test fixtures as scientific data.

Required top-level fields:
- `schema_version`: `terrascan.ml-training.v1`
- `feature_names`: ordered unique numeric feature names
- `samples`: labelled records

Each sample requires `sample_id`, explicit `label`, `label_basis`, `features` (exactly the declared keys, finite numeric values), and `source` with `source_id` and lowercase 64-character SHA-256. Retain the source product, extraction configuration, spatial/temporal sampling method, label reviewer and label uncertainty in your accompanying records. This CLI validates provenance shape, not scientific correctness or label quality.

See `docs/backend/STAGE26_ML_TERRAIN_PATTERN_RECOGNITION.md`. No sample data is included.
