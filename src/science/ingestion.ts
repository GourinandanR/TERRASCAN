import type { DatasetRecord } from "../data/datasetCatalog";

export type IngestionManifest = {
  datasetId: string;
  sourceUrl: string;
  sourceTitle: string;
  provider: string;
  retrievedAt: string;
  fileName: string;
  checksumSha256: string;
  fileFormat: string;
  productVersion: string;
  coordinateReference: string;
  spatialResolution: string;
  units: string;
  spatialCoverage: string;
  temporalCoverage: string;
  processingSteps: string[];
  qualityFlags: string[];
  uncertaintyDescription: string;
  operatorNotes: string;
};

export type IngestionValidation = {
  valid: boolean;
  errors: string[];
  warnings: string[];
};

const requiredText: (keyof IngestionManifest)[] = [
  "datasetId", "sourceUrl", "sourceTitle", "provider", "retrievedAt",
  "fileName", "checksumSha256", "fileFormat", "productVersion",
  "coordinateReference", "spatialResolution", "units", "spatialCoverage",
  "temporalCoverage", "uncertaintyDescription",
];

export function validateIngestionManifest(
  manifest: IngestionManifest,
  catalogRecord?: DatasetRecord,
): IngestionValidation {
  const errors: string[] = [];
  const warnings: string[] = [];

  for (const key of requiredText) {
    if (typeof manifest[key] !== "string" || !String(manifest[key]).trim()) {
      errors.push(`${key} is required.`);
    }
  }

  if (manifest.checksumSha256 && !/^[a-fA-F0-9]{64}$/.test(manifest.checksumSha256)) {
    errors.push("checksumSha256 must be a 64-character SHA-256 hex digest.");
  }
  if (manifest.retrievedAt && Number.isNaN(Date.parse(manifest.retrievedAt))) {
    errors.push("retrievedAt must be a valid date/time.");
  }
  if (!Array.isArray(manifest.processingSteps) || manifest.processingSteps.length === 0) {
    warnings.push("No processing steps recorded; confirm whether the file is an untouched source product.");
  }
  if (!Array.isArray(manifest.qualityFlags) || manifest.qualityFlags.length === 0) {
    warnings.push("No quality flags recorded.");
  }
  if (catalogRecord && catalogRecord.id !== manifest.datasetId) {
    errors.push("Manifest datasetId does not match the selected catalog record.");
  }
  if (catalogRecord && manifest.sourceUrl && !manifest.sourceUrl.startsWith("https://")) {
    warnings.push("Source URL is not HTTPS; verify the official archive and transport security.");
  }

  return { valid: errors.length === 0, errors, warnings };
}
