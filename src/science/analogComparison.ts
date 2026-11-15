import { analogSites } from "../data/analogSites";

export type FeatureKey = "slope" | "roughness" | "thermal" | "elevationRange" | "geology";
export type FeatureUnit = "degree" | "m" | "K" | "class";

export type FeatureObservation = {
  siteId: string;
  feature: FeatureKey;
  value: number | string;
  unit: FeatureUnit;
  uncertainty?: number;
  sourceDatasetId: string;
  sourceUrl: string;
  method: string;
  quality: "high" | "medium" | "low" | "unassessed";
};

export type TargetFeature = {
  target: "Moon" | "Mars";
  feature: FeatureKey;
  minimum?: number;
  maximum?: number;
  category?: string;
  unit: FeatureUnit;
  sourceDatasetId: string;
  sourceUrl: string;
  rationale: string;
};

export type ComparisonFeatureResult = {
  feature: FeatureKey;
  status: "matched" | "missing-observation" | "missing-target" | "unit-mismatch" | "invalid-value";
  similarity: number | null;
  observation: FeatureObservation | null;
  target: TargetFeature | null;
};

export type AnalogComparisonResult = {
  siteId: string;
  target: "Moon" | "Mars";
  score: number | null;
  coverage: number;
  confidence: number | null;
  rank: number | null;
  featureResults: ComparisonFeatureResult[];
  explanation: string;
};

export const comparisonFeatures: { key: FeatureKey; label: string; unit: FeatureUnit; weight: number }[] = [
  { key: "slope", label: "Slope distribution", unit: "degree", weight: 0.25 },
  { key: "roughness", label: "Surface roughness", unit: "m", weight: 0.20 },
  { key: "thermal", label: "Thermal environment", unit: "K", weight: 0.25 },
  { key: "elevationRange", label: "Elevation range", unit: "m", weight: 0.15 },
  { key: "geology", label: "Geological class", unit: "class", weight: 0.15 },
];

// Unit conversion is deliberately narrow and explicit. No implicit CRS, datum or
// planetary-unit conversion is performed by this feature comparison layer.
const convert = (value: number, from: FeatureUnit, to: FeatureUnit): number | null => {
  if (from === to) return value;
  if (from === "m" && to === "m") return value;
  if (from === "K" && to === "K") return value;
  if (from === "degree" && to === "degree") return value;
  return null;
};

function scoreFeature(observation: FeatureObservation, target: TargetFeature): number | null {
  if (observation.unit !== target.unit) return null;
  if (target.category !== undefined) {
    if (typeof observation.value !== "string") return null;
    return observation.value.trim().toLowerCase() === target.category.trim().toLowerCase() ? 100 : 0;
  }
  if (typeof observation.value !== "number" ||
      typeof target.minimum !== "number" ||
      typeof target.maximum !== "number" ||
      !Number.isFinite(observation.value) ||
      target.maximum <= target.minimum) return null;
  const value = convert(observation.value, observation.unit, target.unit);
  if (value === null) return null;
  if (value >= target.minimum && value <= target.maximum) return 100;
  const span = target.maximum - target.minimum;
  const distance = value < target.minimum ? target.minimum - value : value - target.maximum;
  return Math.max(0, 100 * (1 - distance / span));
}

export function compareAnalogSite(
  siteId: string,
  targetBody: "Moon" | "Mars",
  observations: FeatureObservation[],
  targetFeatures: TargetFeature[],
): AnalogComparisonResult {
  const siteExists = analogSites.some((site) => site.id === siteId);
  if (!siteExists) throw new Error(`Unknown analog site: ${siteId}`);

  const featureResults: ComparisonFeatureResult[] = comparisonFeatures.map((definition) => {
    const observation = observations.find((item) => item.siteId === siteId && item.feature === definition.key) ?? null;
    const target = targetFeatures.find((item) => item.target === targetBody && item.feature === definition.key) ?? null;
    if (!observation) return { feature: definition.key, status: "missing-observation", similarity: null, observation, target };
    if (!target) return { feature: definition.key, status: "missing-target", similarity: null, observation, target };
    if (observation.unit !== target.unit) return { feature: definition.key, status: "unit-mismatch", similarity: null, observation, target };
    const similarity = scoreFeature(observation, target);
    if (similarity === null) return { feature: definition.key, status: "invalid-value", similarity: null, observation, target };
    return { feature: definition.key, status: "matched", similarity, observation, target };
  });

  const matched = featureResults.filter((item) => item.status === "matched");
  const coverage = Math.round((matched.length / comparisonFeatures.length) * 100);
  const requiredComplete = matched.length === comparisonFeatures.length;
  const score = requiredComplete
    ? Math.round(featureResults.reduce((sum, item) => {
        const weight = comparisonFeatures.find((feature) => feature.key === item.feature)!.weight;
        return sum + (item.similarity ?? 0) * weight;
      }, 0))
    : null;

  const qualityValues = matched.map((item) => item.observation!.quality);
  const qualityScore: Record<FeatureObservation["quality"], number | null> = {
    high: 1, medium: 0.7, low: 0.4, unassessed: null,
  };
  const confidenceSamples = qualityValues.map((value) => qualityScore[value]).filter((v): v is number => v !== null);
  const confidence = score === null || confidenceSamples.length !== matched.length
    ? null
    : Math.round(confidenceSamples.reduce((a, b) => a + b, 0) / confidenceSamples.length * 100);

  const missing = featureResults.filter((item) => item.status !== "matched").map((item) => item.feature);
  return {
    siteId, target: targetBody, score, coverage, confidence, rank: null, featureResults,
    explanation: score === null
      ? `Ranking withheld: ${missing.length} of ${comparisonFeatures.length} feature pairs are missing or incompatible.`
      : "All configured feature pairs are present and unit-compatible. This is a feature-level research comparison, not mission suitability.",
  };
}

export function rankAnalogSites(
  target: "Moon" | "Mars",
  observations: FeatureObservation[],
  targetFeatures: TargetFeature[],
): AnalogComparisonResult[] {
  const results = analogSites.map((site) => compareAnalogSite(site.id, target, observations, targetFeatures));
  const eligible = results.filter((item) => item.score !== null).sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
  eligible.forEach((item, index) => { item.rank = index + 1; });
  return results;
}
