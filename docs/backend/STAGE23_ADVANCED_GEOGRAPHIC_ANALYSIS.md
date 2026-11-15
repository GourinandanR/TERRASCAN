# Stage 23 — Advanced Planetary Geospatial Analysis

## Purpose
Stage 23 adds reproducible, multiscale descriptive terrain analysis for a raster that has already passed through the Stage 22 validation workflow. It is deliberately not an analog classifier, similarity scorer, or mission-suitability engine.

## Requirements
Install the optional geospatial dependencies in a compatible environment:
```bash
pip install -r requirements-geo.txt
```
The script uses Rasterio, NumPy and SciPy.

## Run
```bash
python scripts/terrascan_spatial.py path/to/dem.tif \
  --validation-report data/validation/DEM-mars-validation.json \
  --body Mars --band 1 --windows 3 7 15 --pixel-size-units m
```
`--pixel-size-units` must come from authoritative product documentation. It is not inferred from CRS names or pixel values. Window sizes are odd pixel counts; report dimensions are approximate products of pixel spacing and window width.

## Outputs
An immutable JSON report is written under `data/spatial-analysis/` unless `--output` is supplied. It includes:
- source and Stage 22 validation report SHA-256 hashes;
- target body and raster metadata;
- valid/invalid pixel counts and robust elevation/value distribution summaries;
- multiscale topographic position index (center minus local mean), local elevation standard deviation and a terrain-ruggedness proxy at each requested window;
- explicit limitations and review disposition.

## Guardrails
- The validation report must match the requested body and must contain zero failed checks. Unknown Stage 22 checks are allowed only as a visible review-required state.
- No CRS conversion, resampling, scale interpretation beyond raster scale/offset metadata, unit conversion, cross-body comparison, or evidence approval is performed.
- Neighborhood windows with any no-data pixels are excluded to avoid partial-window artefacts.
- The metrics are scale-dependent descriptive statistics. They are not validated landform classes, physical roughness standards, similarity scores, rankings, or mission conclusions.
- A recognized CRS and a no-fail metadata report do not establish planetary frame correctness; the official product label and documentation remain authoritative.

## Validation
Offline synthetic raster tests cover multiscale calculations, Stage 22 body mismatch rejection, failed-validation rejection, required explicit pixel-spacing units and immutable output behavior.
