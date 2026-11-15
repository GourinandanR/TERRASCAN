# Stage 8 — Controlled Local Data Store & Raster Inspection

## Implemented

`scripts/terrascan_ingest.py` adds a Python CLI with three operations:

- `download`: accepts a catalogue ID and a direct HTTPS product URL; applies a per-dataset host allow-list, rejects cross-host redirects, streams to a temporary file, computes SHA-256, supports an optional expected digest and enforces a default 20 GiB size limit.
- `inspect`: re-hashes a local file and uses Rasterio when installed to report driver, dimensions, bands, data types, CRS, transform, bounds, resolution, no-data, units, scale/offset and tags.
- `manifest`: re-checks the source digest and creates a provenance manifest marked `pending-human-review`.

Raw files are stored at `data/raw/<dataset-id>/<sha256>/<filename>`. The tool refuses to overwrite a content-addressed file. The raw file is never modified by inspection or manifest creation.

## Setup

Python 3.10+ is recommended. Rasterio is optional for downloading and hashing, but required for richer geospatial metadata inspection.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-geo.txt
```

Rasterio may require platform-specific GDAL wheels. If installation fails, use a compatible conda-forge environment or follow the official Rasterio installation guidance. The downloader and hashing use only Python standard-library modules.

## Download a specific archive product

Select a direct product-file URL from the official archive page; do not pass a general landing page as though it were a data file.

```bash
python scripts/terrascan_ingest.py download --dataset-id mars-mola-megdr --url "https://pds-geosciences.wustl.edu/.../product.img" --filename "product.img" --expected-sha256 "<published-digest-if-available>"
```

The hostname must be on the allow-list for that dataset ID. If an official archive redirects to another host, verify the redirect and update the allow-list in source control; do not bypass the redirect protection.

## Inspect and create a pending manifest

```bash
python scripts/terrascan_ingest.py inspect "data/raw/mars-mola-megdr/<sha256>/product.img" --dataset-id mars-mola-megdr
python scripts/terrascan_ingest.py manifest "data/inspection/<report>.json" --dataset-id mars-mola-megdr --source-url "https://official-product-url" --provider "NASA PDS Geosciences Node" --product-version "label-derived-version"
```

## Review gates

A manifest is a provenance record, not scientific approval. Compare the raster report with the original product label and documentation. Human review must confirm product ID/version, instrument, planetary reference frame, projection, longitude convention, vertical datum, units, scale/offset, no-data, resolution, spatial footprint, temporal coverage, quality flags and uncertainty. Record all processing commands and software versions for derived products.

Rasterio's CRS and bounds output does not itself prove that a planetary CRS is interpreted correctly. Some products require specialized PDS/ISIS/GDAL drivers or explicit mapping metadata. No raster reprojection, resampling, clipping or science measurements are generated automatically by this stage.

## Data directories

- `data/raw/` — content-addressed source files; do not edit in place.
- `data/inspection/` — inspection JSON reports.
- `data/manifests/` — provenance manifests awaiting review.
- `data/derived/` — reserved for separately stored reproducible derivatives.

No live product URL or version is assumed, and no source raster is bundled by this stage.
