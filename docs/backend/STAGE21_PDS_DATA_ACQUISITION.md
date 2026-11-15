# Stage 21 — Mission Data Integration & Scientific Evidence Acquisition

## NASA PDS Search API integration
TERRASCAN now includes `scripts/terrascan_pds.py`, a standard-library client for the NASA PDS Search API at `https://pds.nasa.gov/api/search/1`.

Examples:
```bash
python scripts/terrascan_pds.py search --keywords MOLA --limit 20
python scripts/terrascan_pds.py search --keywords LOLA --limit 20
python scripts/terrascan_pds.py search --query 'target_name eq "Mars"' --limit 20
python scripts/terrascan_pds.py resolve urn:nasa:pds:some.logical.identifier
```
The exact query syntax and searchable field names depend on PDS Search API metadata properties. Search output is saved as immutable JSON snapshots under `data/pds-search/`, including request URL, retrieval timestamp, response SHA-256, normalized convenience fields and the complete raw API response. Search snapshots are discovery records only.

The PDS documentation states that the search API supports product search, identifier resolution and archive hierarchy traversal. It also warns that the API servers are not fully populated; empty search results do not prove a product does not exist.

## Controlled file acquisition
Use the existing `scripts/terrascan_ingest.py download` command after selecting a verified direct HTTPS file URL from an official product/label record:
```bash
python scripts/terrascan_ingest.py download --dataset-id mars-mola-megdr --url "https://<official-allow-listed-host>/<file>" --expected-sha256 <official-checksum>
```
Only configured HTTPS hosts are accepted; redirects must remain HTTPS on the same host; downloads are size-limited, streamed and SHA-256 hashed. The process does not follow arbitrary API-supplied URLs or auto-download every search result. Cross-host redirects are rejected intentionally. Use a direct archive product URL on an allow-listed host.

## Label and raster inspection
The ingestion inspector now extracts selected XML/PDS4-like label values into the inspection report, alongside Rasterio metadata when available. Extracted values are hints, not scientific validation. PDS3 labels, binary tables, special encodings and complex product layouts may require mission/node-specific readers. Verify label namespace semantics, coordinate system, body-fixed frame, longitude convention, map projection, scale/offset, units, no-data values, uncertainty, quality flags, spatial footprint and temporal coverage.

## Evidence gates
- Search metadata is never inserted as a scientific observation.
- Downloaded files are content-addressed and checksum-protected.
- Inspection reports are not approvals.
- Manifests remain pending human review.
- Existing API review gates still require human approval before observations can be registered.
- No planetary measurements, mission thresholds or similarity/suitability scores are fabricated.

## API caveat
The PDS Search API is a federated registry; archive coverage and available metadata differ among nodes and products. A product may be discoverable but not directly downloadable from the same hostname. The controlled downloader's same-host redirect policy may require a separately verified direct URL from the official node. This is a deliberate security boundary, not an indication that the product is unavailable.
