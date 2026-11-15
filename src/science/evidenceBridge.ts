import type { DatasetRecord } from "../data/datasetCatalog";
import type { CriterionEvidence } from "./types";
import type { IngestionManifest } from "./ingestion";

export type EvidenceBridgeResult = { valid: boolean; errors: string[]; warnings: string[] };

/**
 * Checks the traceability link between a proposed science measurement and its
 * ingested dataset manifest. This is a consistency gate, not scientific review.
 */
export function validateEvidenceBridge(
  evidence: CriterionEvidence,
  manifest: IngestionManifest,
  dataset: DatasetRecord,
): EvidenceBridgeResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (evidence.source.datasetId !== manifest.datasetId) errors.push("Evidence source datasetId does not match the ingestion manifest.");
  if (manifest.datasetId !== dataset.id) errors.push("Manifest datasetId does not match the selected catalog record.");
  if (evidence.criterionId !== dataset.criterion) errors.push("Evidence criterion does not match the catalog criterion.");
  if (!evidence.source.title.trim() || !evidence.source.organization.trim()) errors.push("Evidence source title and organization are required.");
  if (!evidence.source.url.startsWith("https://")) warnings.push("Evidence source URL is not HTTPS; verify the archive location.");
  if (evidence.unit.trim().toLowerCase() !== manifest.units.trim().toLowerCase()) {
    warnings.push("Evidence unit differs from the manifest units; confirm a documented conversion or product-specific unit selection.");
  }
  if (evidence.quality === "unassessed") warnings.push("Evidence quality has not been assessed; it should not be treated as validated science.");
  if (evidence.comparability === "unknown") warnings.push("Evidence comparability is unknown; similarity scoring may be inappropriate.");
  if (!/^[a-f0-9]{64}$/i.test(manifest.checksumSha256)) errors.push("Manifest checksum is not a valid SHA-256 digest.");
  return { valid: errors.length === 0, errors, warnings };
}
