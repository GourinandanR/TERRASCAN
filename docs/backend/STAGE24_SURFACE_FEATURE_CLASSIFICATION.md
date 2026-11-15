# Stage 24 — Planetary Surface Feature Extraction & Classification

## Purpose
Stage 24 derives slope, topographic position and local elevation variability from an input raster, then assigns deterministic class IDs using an operator-supplied rule configuration. It is intentionally transparent and is **not** a trained machine-learning model or a validated geological taxonomy.

## Requirements
Install optional geospatial dependencies:
```bash
pip install -r requirements-geo.txt
```
The runtime requires Rasterio, NumPy and SciPy.

## Configuration
Create a JSON file with schema version 1.0. All thresholds are explicit and user-defined. No scientifically meaningful default classes or thresholds are supplied:
```json
{
  "schemaVersion": "1.0",
  "name": "reviewed project rules",
  "classes": [
    {
      "name": "example-class-name",
      "slopeDegrees": [0, 10],
      "tpi": [-5, 5],
      "localStdDev": [0, 20]
    }
  ]
}
```
Each range is `[minimum, maximum]`; either endpoint may be `null` for an open bound. Values must be justified for the target product and scale. Classes are evaluated in listed order; the first matching class wins.

## Run
```bash
python scripts/terrascan_classify.py path/to/dem.tif \
  --validation-report data/validation/DEM-mars-validation.json \
  --config path/to/reviewed-rules.json --body Mars \
  --band 1 --window 3 --pixel-size-units m --vertical-units m
```
A Stage 22 validation report for the same body is required, and any failed validation check blocks classification. Explicit metric horizontal and vertical units are required; geographic-degree grids are rejected for slope calculation.

## Outputs
- `data/surface-classification/*-classes.tif`: UInt16 class IDs; zero means no-data, incomplete neighbourhood, or no rule matched.
- `data/surface-classification/*-classification.json`: immutable report containing source, validation, config and output SHA-256 hashes, counts, class rules, and limitations.

## Scientific and operational safeguards
- The output is exploratory and pending human review; no evidence approval changes.
- No analog similarity scores, site rankings, mission suitability or mission authorization are computed.
- The rule engine is deterministic and user-configured. It is not a learned model; no training dataset or model accuracy is claimed.
- Class precedence is determined by config order. Overlapping ranges must be reviewed before interpretation.
- Product-specific planetary frame, map projection distortion, vertical datum, scale/offset, uncertainty and quality flags still require authoritative product documentation and human review.

## Validation
Synthetic offline tests cover raster output, hashes, body mismatch rejection, failed Stage 22 validation, malformed rule thresholds and immutable output behavior.
