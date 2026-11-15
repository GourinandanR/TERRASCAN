export type PlanetaryTarget = "Moon" | "Mars";
export type CriterionCategory =
  | "geology"
  | "terrain"
  | "thermal"
  | "atmosphere"
  | "radiation"
  | "resources"
  | "operations";

export type ComparisonMethod = "range" | "target-value" | "categorical";

export type CriterionDefinition = {
  id: string;
  label: string;
  category: CriterionCategory;
  description: string;
  unit: string;
  method: ComparisonMethod;
  required: boolean;
  defaultWeight: number;
  evidenceGuidance: string;
};

export type EvidenceSource = {
  title: string;
  organization: string;
  url: string;
  datasetId: string;
  accessedAt: string;
  publicationDate?: string;
};

export type CriterionEvidence = {
  siteId: string;
  target: PlanetaryTarget;
  criterionId: string;
  observedValue: number | string;
  unit: string;
  uncertainty?: number;
  resolution?: string;
  temporalCoverage?: string;
  comparability: "high" | "medium" | "low" | "unknown";
  quality: "high" | "medium" | "low" | "unassessed";
  source: EvidenceSource;
};

export type TargetReference = {
  target: PlanetaryTarget;
  criterionId: string;
  method: ComparisonMethod;
  unit: string;
  minimum?: number;
  maximum?: number;
  targetValue?: number | string;
  rationale: string;
  source: EvidenceSource;
};

export type MissionGate = {
  id: string;
  label: string;
  status: "pass" | "fail" | "unknown";
  rationale: string;
  source?: EvidenceSource;
};

export type CriterionResult = {
  criterionId: string;
  label: string;
  category: CriterionCategory;
  weight: number;
  evidenceStatus: "missing-evidence" | "missing-reference" | "unit-mismatch" | "available";
  similarity: number | null;
  evidence: CriterionEvidence | null;
};

export type SimilarityAssessment = {
  siteId: string;
  target: PlanetaryTarget;
  similarityScore: number | null;
  dataCompleteness: number;
  confidenceScore: number | null;
  missionSuitability: "not-assessed" | "blocked" | "requirements-met" | "requirements-not-met";
  criterionResults: CriterionResult[];
  missingRequired: string[];
  rationale: string;
};
