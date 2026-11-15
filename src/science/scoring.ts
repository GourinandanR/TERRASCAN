import { criterionDefinitions, defaultWeights } from "./criteria";
import type {
  CriterionEvidence,
  MissionGate,
  SimilarityAssessment,
  TargetReference,
  PlanetaryTarget,
} from "./types";

export type AssessmentInput = {
  siteId: string;
  target: PlanetaryTarget;
  evidence: CriterionEvidence[];
  references: TargetReference[];
  gates?: MissionGate[];
  weights?: Record<string, number>;
};

function similarityFor(
  evidence: CriterionEvidence,
  reference: TargetReference,
): number | null {
  if (evidence.unit.trim().toLowerCase() !== reference.unit.trim().toLowerCase()) {
    return null;
  }

  if (reference.method === "range") {
    if (typeof evidence.observedValue !== "number" ||
        typeof reference.minimum !== "number" ||
        typeof reference.maximum !== "number" ||
        reference.maximum <= reference.minimum) return null;

    const value = evidence.observedValue;
    if (value >= reference.minimum && value <= reference.maximum) return 100;

    const span = reference.maximum - reference.minimum;
    const distance = value < reference.minimum
      ? reference.minimum - value
      : value - reference.maximum;
    return Math.max(0, 100 * (1 - distance / span));
  }

  if (reference.method === "target-value") {
    if (typeof evidence.observedValue !== "number" ||
        typeof reference.targetValue !== "number") return null;
    const scale = Math.max(Math.abs(reference.targetValue), 1);
    const relativeDistance = Math.abs(evidence.observedValue - reference.targetValue) / scale;
    return Math.max(0, 100 * (1 - relativeDistance));
  }

  if (reference.method === "categorical") {
    if (typeof evidence.observedValue !== "string" ||
        typeof reference.targetValue !== "string") return null;
    return evidence.observedValue.trim().toLowerCase() === reference.targetValue.trim().toLowerCase()
      ? 100
      : 0;
  }

  return null;
}

function confidenceFor(evidence: CriterionEvidence): number | null {
  const quality: Record<CriterionEvidence["quality"], number | null> = {
    high: 1,
    medium: 0.7,
    low: 0.4,
    unassessed: null,
  };
  const comparability: Record<CriterionEvidence["comparability"], number | null> = {
    high: 1,
    medium: 0.7,
    low: 0.4,
    unknown: null,
  };
  const q = quality[evidence.quality];
  const c = comparability[evidence.comparability];
  if (q === null || c === null) return null;
  return Math.round(100 * Math.sqrt(q * c));
}

export function assessAnalog(input: AssessmentInput): SimilarityAssessment {
  const weights = input.weights ?? defaultWeights;
  const evidenceByCriterion = new Map(
    input.evidence
      .filter((item) => item.siteId === input.siteId && item.target === input.target)
      .map((item) => [item.criterionId, item]),
  );
  const referencesByCriterion = new Map(
    input.references
      .filter((item) => item.target === input.target)
      .map((item) => [item.criterionId, item]),
  );

  const criterionResults = criterionDefinitions.map((criterion) => {
    const evidence = evidenceByCriterion.get(criterion.id) ?? null;
    const reference = referencesByCriterion.get(criterion.id) ?? null;
    let evidenceStatus: "missing-evidence" | "missing-reference" | "unit-mismatch" | "available";
    let similarity: number | null = null;

    if (!evidence) evidenceStatus = "missing-evidence";
    else if (!reference) evidenceStatus = "missing-reference";
    else {
      similarity = similarityFor(evidence, reference);
      evidenceStatus = similarity === null
        ? (evidence.unit.trim().toLowerCase() !== reference.unit.trim().toLowerCase() ? "unit-mismatch" : "missing-reference")
        : "available";
    }

    return {
      criterionId: criterion.id,
      label: criterion.label,
      category: criterion.category,
      weight: weights[criterion.id] ?? criterion.defaultWeight,
      evidenceStatus,
      similarity,
      evidence,
    };
  });

  const required = criterionDefinitions.filter((criterion) => criterion.required);
  const missingRequired = criterionResults
    .filter((result) => {
      const definition = criterionDefinitions.find((item) => item.id === result.criterionId);
      return definition?.required && result.evidenceStatus !== "available";
    })
    .map((result) => result.label);

  const availableCount = criterionResults.filter((result) => result.evidenceStatus === "available").length;
  const dataCompleteness = Math.round((availableCount / required.length) * 100);

  const scored = criterionResults.filter((result) => result.similarity !== null);
  const totalWeight = scored.reduce((sum, result) => sum + result.weight, 0);
  const similarityScore = missingRequired.length === 0 && totalWeight > 0
    ? Math.round(scored.reduce((sum, result) => sum + (result.similarity ?? 0) * result.weight, 0) / totalWeight)
    : null;

  const confidenceValues = criterionResults
    .filter((result) => result.evidenceStatus === "available" && result.evidence)
    .map((result) => confidenceFor(result.evidence!))
    .filter((value): value is number => value !== null);
  const confidenceScore = confidenceValues.length === 0
    ? null
    : Math.round(confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length);

  const gates = input.gates ?? [];
  const missionSuitability = gates.length === 0
    ? "not-assessed"
    : gates.some((gate) => gate.status === "fail")
      ? "requirements-not-met"
      : gates.some((gate) => gate.status === "unknown")
        ? "blocked"
        : "requirements-met";

  return {
    siteId: input.siteId,
    target: input.target,
    similarityScore,
    dataCompleteness,
    confidenceScore,
    missionSuitability,
    criterionResults,
    missingRequired,
    rationale: similarityScore === null
      ? "No aggregate similarity score is issued because one or more required evidence/reference pairs are missing or incompatible."
      : "All required criteria have compatible evidence and target references. The score is a weighted comparison under the configured project model.",
  };
}
