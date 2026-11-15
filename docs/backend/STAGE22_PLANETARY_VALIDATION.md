# Stage 22 — Planetary Raster Intelligence & Scientific Data Validation

## Purpose
Stage 22 adds a conservative, reproducible validation report for existing Stage 8 inspection JSON and an optional PDS4 XML label. It does not alter source rasters, manifests, observations, approvals, or scientific values.

## Run

```bash
python scripts/terrascan_validate.py data/inspection/<inspection>.json --expected-body Mars --label /path/to/product.xml
```

Use `--output /path/to/new-report.json` to choose a report destination. Existing reports are never overwritten. Without `--output`, reports are written under `data/validation/`.

## Checks
- Target body consistency between the inspection and requested body.
- Raster read state, dimensions, positive finite resolution, ordered finite bounds.
- Presence of CRS and band units; absent values remain `unknown`.
- Guard against common Earth-centric CRS identifiers on Moon/Mars datasets.
- No-data metadata presence (metadata-only; no pixel mask evaluation).
- Optional PDS XML label parse, target-body hints, reference-frame hints and unit declarations.

## Interpretation
`fail` means a detected contradiction or invalid metadata condition. `review-required` means no failure was detected but at least one required detail remains unknown. `checks-passed` means only that these limited metadata rules passed; it is not a scientific certification. Every report is marked `scientificDisposition: not-approved` and leaves evidence approval unchanged.

## Important limitations
A CRS recognized by GDAL/Rasterio is not proof that the correct lunar/Martian body-fixed frame, datum, axis order, longitude direction or projection has been selected. PDS labels may contain repeated generic `<name>`, `<value>` and `<unit>` elements; this stage records hints and does not claim a full schema-aware PDS4 interpretation. It does not perform coordinate conversion, unit conversion, resampling, pixel-level no-data/quality checks, resolution plausibility checks against mission product specifications, or scientific calibration. Review the complete authoritative label and product documentation.

## Tests

```bash
python -m unittest scripts.test_terrascan_validate -v
```
