import type { IngestionManifest } from "../science/ingestion";

/**
 * Empty by design. Add a manifest only after an actual archive product has
 * been downloaded, checksummed and inspected. Catalog entries are not ingested data.
 */
export const ingestionManifests: IngestionManifest[] = [];
