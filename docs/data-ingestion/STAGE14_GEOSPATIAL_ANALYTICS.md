# Stage 14 — Advanced Geospatial Analytics & Scientific Feature Extraction

## Purpose
Stage 14 adds a controlled site-feature extraction step after Stage 9 raster preparation. It calculates descriptive Earth analog-candidate features from aligned elevation, slope, thermal, and categorical geology rasters and emits a provenance-rich JSON review package.

## Extracted features
- **Slope:** mean slope in degrees, plus count/min/max/mean/std/median/p90.
- **Roughness:** mean of a local DEM elevation standard-deviation surface in metres. This is one explicitly defined roughness proxy, not a universal geomorphic roughness measure.
- **Thermal environment:** mean and descriptive distribution in Kelvin.
- **Elevation range:** maximum minus minimum DEM elevation in metres.
- **Geology:** dominant categorical class and per-class pixel counts using a user-supplied legend mapping.

## Preconditions
1. Install `requirements-geo.txt` in a compatible environment.
2. Use Stage 9 to prepare rasters on exactly the same grid.
3. Confirm each source product's CRS, datum/body-fixed frame, band units, scale, offset, nodata, spatial resolution, temporal coverage, and quality from its official label.
4. Produce the slope raster using the Stage 9 terrain command.
5. Supply a GeoJSON FeatureCollection whose polygons have already been reprojected to the raster CRS.
6. Supply a geology class mapping JSON whose class names come from the authoritative map legend.

The tool rejects missing/mismatched CRS, units, dimensions, affine transforms, site IDs, duplicate IDs, and unmapped geology values. It does not reproject or resample implicitly.

## Example
Create `data/site-zones.geojson` with a `site_id` property and `data/geology-classes.json` such as:

```json
{
  "1": "legend class label from source map",
  "2": "another authoritative legend label"
}
```

Run (replace paths and CRS with values verified from your source products):

```bash
python scripts/terrascan_features.py extract \
  --dem data/derived/common-grid/dem_grid.tif \
  --slope data/derived/terrain/dem_slope_degrees.tif \
  --thermal data/derived/common-grid/thermal_grid.tif \
  --geology data/derived/common-grid/geology_grid.tif \
  --geojson data/site-zones.geojson \
  --zone-crs EPSG:32619 \
  --site-id-field site_id \
  --geology-classes data/geology-classes.json \
  --output-name earth-analog-sites
```

The example CRS is illustrative only; it must be replaced with the actual verified CRS. The tool expects DEM units `m`, slope units `degree`, and thermal units `K` recorded on raster bands. Geology class values are read as categorical integer/numeric values and mapped exactly.

Output:
`data/derived/site-features/earth-analog-sites.features.json`

Use `--overwrite` only when intentionally replacing an existing derived report. Source rasters are read-only and SHA-256 hashes are embedded in the report.

## Review and API workflow
The output status is always `pending-human-review`. It is a derived feature report, not an approved evidence record. Review the official source labels and the output report, then manually register individual approved observations through the Stage 12 API. The Stage 14 script does not auto-submit evidence or create comparison runs.

## Validation
`python -m unittest scripts.test_terrascan_features -v`

The synthetic test creates temporary rasters and polygons to exercise the extraction code. It validates software behavior only, not scientific interpretations or real planetary/Earth data.
