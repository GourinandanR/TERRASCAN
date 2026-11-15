# Stage 13 — Automated Scientific Data Pipeline

## Scope

Stage 13 adds a deterministic batch orchestrator around the existing Stage 8 controlled downloader/inspector/manifest generator and Stage 12 API. It does not change the scientific scoring model and does not create observations or target values.

## Pipeline behavior

1. Read a project-local JSON job file.
2. Restrict dataset IDs to the controlled catalogue.
3. Resolve each input file under the project root (path traversal is rejected).
4. Recompute SHA-256 and optionally compare with `expected_sha256`.
5. Run the existing raster/file inspection command.
6. Create a checksum-bound provenance manifest if one does not already exist.
7. Keep every generated manifest at `pending-human-review`.
8. Optionally submit the manifest to the Stage 12 API when `--sync-api` is explicitly supplied.
9. Write a per-run JSON report to `data/pipeline-runs/` and continue after job failures unless `--stop-on-error` is set.

The orchestrator itself does not download files. Use the existing controlled `terrascan_ingest.py download` command for HTTPS allow-listed retrieval before scheduling local files in the batch config. This separation makes network retrieval an explicit action.

## Configure a batch

Copy `data/pipeline/jobs.example.json` to `data/pipeline/jobs.json` and add entries. Example shape:

```json
{
  "jobs": [
    {
      "dataset_id": "mars-mola-megdr",
      "file": "data/raw/mars-mola-megdr/<sha256>/product.tif",
      "source_url": "https://pds-geosciences.wustl.edu/your-verified-product",
      "provider": "NASA PDS Geosciences Node",
      "source_title": "Verified product title from its label",
      "product_version": "Version from official label",
      "expected_sha256": "optional 64-character checksum"
    }
  ]
}
```

Replace placeholders with an actual local file and verified metadata. Do not use this example as a real product citation.

## Run

```bash
python scripts/terrascan_pipeline.py data/pipeline/jobs.json
```

Optional Stage 12 API sync:

```bash
python scripts/terrascan_pipeline.py data/pipeline/jobs.json --sync-api http://127.0.0.1:8000
```

Run the API first. API synchronization registers provenance metadata only; the API rejects observation creation unless the referenced manifest has separately passed human approval.

## Tests

```bash
python -m unittest scripts/test_terrascan_pipeline.py -v
```

## Safety and scientific limitations

- No network download occurs inside the batch orchestrator.
- HTTPS retrieval remains governed by the existing dataset host allow-list and same-host redirect policy.
- Existing files are never overwritten by this pipeline.
- Checksums are recomputed from the local file.
- Existing manifests are reused only when their checksum matches the file.
- Raster metadata inspection is not scientific validation.
- CRS/body-fixed frame, units, scale/offset, no-data, spatial/temporal footprint, quality and uncertainty still require expert review against official product documentation.
- No manifest is automatically approved; no evidence observations or similarity scores are created.
