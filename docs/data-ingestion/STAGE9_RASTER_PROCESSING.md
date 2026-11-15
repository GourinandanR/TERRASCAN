# Stage 9 — Planetary Raster Processing & Analog Feature Extraction

## Commands

Requires the optional geospatial dependencies in `requirements-geo.txt` (Rasterio, NumPy and PyProj).

### 1. Explicit common-grid preparation

```bash
python scripts/terrascan_process.py grid input.tif --target-crs "EPSG:XXXX" --resolution 100 --resampling bilinear
```

The target CRS and resolution are mandatory. Resolution is expressed in target CRS coordinate units. The output includes a provenance JSON with input/output hashes and processing settings. Do not use one shared CRS across Moon, Mars and Earth unless the planetary reference systems have been explicitly defined and scientifically justified.

### 2. Terrain derivatives

```bash
python scripts/terrascan_process.py terrain dem_projected_metres.tif --band 1
```

The current derivative implementation is intentionally guarded: it requires a projected CRS whose horizontal axes are in metres and an elevation band explicitly tagged in metres. It creates slope (degrees) and aspect (degrees clockwise from north). If product labels do not expose trustworthy units, processing stops rather than guessing. This is a first-pass derivative, not a mission-grade terrain product.

### 3. Site-level zonal statistics

Prepare a GeoJSON FeatureCollection of site polygons and explicitly declare its CRS:

```bash
python scripts/terrascan_process.py zonal raster.tif sites.geojson --zone-crs "EPSG:XXXX" --band 1
```

The polygon CRS must exactly match the raster CRS. Output includes count, minimum, maximum, mean, median and standard deviation for each polygon. The `--all-touched` option changes pixel inclusion and is recorded in the output.

## Output locations

- `data/derived/common-grid/` — explicitly reprojected/resampled rasters and provenance.
- `data/derived/terrain/` — slope/aspect rasters and provenance.
- `data/derived/site-stats/` — zonal-statistics JSON.
- `data/processing/` — reserved for future processing run records.

## Scientific constraints

- Every output records the input SHA-256. Original raw files are not modified.
- A common grid is a geometric alignment convenience, not proof that measurements are comparable.
- Planetary coordinate frames, datum, longitude convention, projection, vertical reference, units, scale/offset and nodata semantics must be confirmed from the official product labels.
- Slope/aspect derivation is refused unless horizontal and vertical units meet the current metre-only assumptions.
- Zonal statistics are descriptive. They are not similarity scores and do not populate the evidence registry automatically.
- No real LOLA, MOLA, THEMIS or Earth analog raster is included in this stage.
