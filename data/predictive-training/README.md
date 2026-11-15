# Predictive terrain training workspace

No predictive training samples are included. Use operator-reviewed records with:
- `schema_version`: `terrascan.predictive-training.v1`
- ordered unique `feature_names`
- `target`: explicit target `name` and `unit`
- `samples`: each with unique `sample_id`, `spatial_group_id`, exact feature keys, finite `target_value`, `target_basis`, and source `source_id` plus lowercase SHA-256.

`spatial_group_id` must represent a meaningful independent spatial sampling unit (e.g. tile, region or site), not an arbitrary per-row ID. The workflow holds groups apart between training, calibration and test partitions to reduce spatial leakage. This is not a substitute for cross-body/cross-sensor validation.

See `docs/backend/STAGE27_PREDICTIVE_TERRAIN_ANALYSIS.md`. Do not use synthetic software test fixtures as scientific training data.
