# Stage 7 — Validated Raster Ingestion & Evidence Bridge

## What is implemented

- `scripts/inspect-dataset.mjs` is a dependency-free local inspector. It computes a SHA-256 digest for the exact file supplied, records byte size and inspection time, parses common ENVI `.hdr` fields, detects classic TIFF/GeoTIFF dimensions and sample metadata, and preserves a bounded preview of PDS/XML labels.
- `src/science/evidenceBridge.ts` checks the traceability relationship between a proposed criterion measurement, its ingestion manifest and the selected catalogue record. It checks identifiers, criterion alignment, source fields, checksum shape and unit consistency warnings.
- Existing manifest validation remains in `src/science/ingestion.ts`.

## Run the inspector

```bash
node scripts/inspect-dataset.mjs ./data/raw/product.img --header ./data/raw/product.hdr > ./data/inspection/product-inspection.json
```

For a TIFF/GeoTIFF:

```bash
node scripts/inspect-dataset.mjs ./data/raw/product.tif > ./data/inspection/product-inspection.json
```

For a PDS label:

```bash
node scripts/inspect-dataset.mjs ./data/raw/product.lbl > ./data/inspection/product-label-inspection.json
```

The JSON output includes the SHA-256 digest. Store it with the source label and the original file. Do not edit or overwrite files under `data/raw/` after hashing.

## Recommended directory layout

```text
data/
  raw/                 # immutable source downloads and original labels
  inspection/          # inspector JSON and human review notes
  derived/              # reprojected/clipped/converted products
  manifests/            # one manifest per ingested product
```

## Required human/technical review before validation

1. Confirm the archive product identifier, version and instrument from the official label.
2. Confirm raster dimensions, sample type, byte order, scale/offset and no-data value.
3. Confirm CRS, body-fixed reference frame, map projection, longitude convention and vertical datum.
4. Confirm physical units and any scale/offset conversion from the product documentation.
5. Confirm spatial footprint and temporal coverage; distinguish global mosaics from regional products.
6. Record quality flags, uncertainty, processing software/version and all transformations.
7. Independently verify the SHA-256 digest after transfer or copy.
8. Only then create an ingestion manifest and candidate evidence record.

## Important limits of the lightweight inspector

This is a provenance and first-pass metadata utility, not a replacement for GDAL, Rasterio, ISIS, or official PDS tools. It does not decode full GeoTIFF georeferencing keys, BigTIFF IFDs, PDS4 XML schemas, compressed raster blocks, planetary coordinate systems, or scientific calibration. Use a domain-appropriate toolchain and the official product label for authoritative interpretation. Never infer a projection, unit, scale factor or datum from a filename or visual appearance.

## Current data state

No planetary raster was downloaded in this stage. `src/data/ingestionManifests.ts` and `src/data/scienceEvidence.ts` remain empty. Therefore no scientific score is unlocked by this stage. The inspector can now be run locally against real source files when obtained from the catalogued official archives.
