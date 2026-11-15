import type { CriterionDefinition, PlanetaryTarget } from "./types";

/**
 * Default weights are starting configuration only, not empirically validated.
 * All criteria remain required until a project administrator explicitly changes
 * the requirement policy and documents the rationale.
 */
export const criterionDefinitions: CriterionDefinition[] = [
  {
    id: "geology",
    label: "Geological composition",
    category: "geology",
    description: "Lithology, mineral assemblages, alteration and regolith composition.",
    unit: "project-defined",
    method: "categorical",
    required: true,
    defaultWeight: 0.20,
    evidenceGuidance: "Use mapped units, laboratory analyses or instrument-derived mineralogy with scale and provenance.",
  },
  {
    id: "terrain",
    label: "Terrain and topography",
    category: "terrain",
    description: "Slope, roughness, elevation range, landforms and traversability.",
    unit: "m / degrees",
    method: "range",
    required: true,
    defaultWeight: 0.18,
    evidenceGuidance: "Use DEM-derived metrics with stated horizontal/vertical resolution, CRS and processing history.",
  },
  {
    id: "thermal",
    label: "Thermal environment",
    category: "thermal",
    description: "Surface or near-surface temperature distribution and thermal cycling.",
    unit: "K",
    method: "range",
    required: true,
    defaultWeight: 0.15,
    evidenceGuidance: "Record sensor depth, local time, season, acquisition period and temperature uncertainty.",
  },
  {
    id: "atmosphere",
    label: "Atmospheric conditions",
    category: "atmosphere",
    description: "Pressure, composition, density, winds and atmospheric variability.",
    unit: "project-defined",
    method: "range",
    required: true,
    defaultWeight: 0.12,
    evidenceGuidance: "Use in-situ or validated atmospheric products; preserve units, altitude and season.",
  },
  {
    id: "radiation",
    label: "Radiation environment",
    category: "radiation",
    description: "Ionizing radiation dose, particle environment and shielding context.",
    unit: "project-defined",
    method: "range",
    required: true,
    defaultWeight: 0.12,
    evidenceGuidance: "Distinguish surface measurements, orbital estimates, shielding assumptions and exposure duration.",
  },
  {
    id: "resources",
    label: "Water and volatile potential",
    category: "resources",
    description: "Evidence for water ice, hydrated minerals and other mission-relevant volatiles.",
    unit: "project-defined",
    method: "range",
    required: true,
    defaultWeight: 0.13,
    evidenceGuidance: "Separate direct detection, spectral inference and modelled resource estimates.",
  },
  {
    id: "operations",
    label: "Operational environment",
    category: "operations",
    description: "Access, communications, illumination, logistics and field safety constraints.",
    unit: "project-defined",
    method: "categorical",
    required: true,
    defaultWeight: 0.10,
    evidenceGuidance: "Use mission-specific operational constraints and clearly identify Earth-only proxies.",
  },
];

export const targetBodies: PlanetaryTarget[] = ["Moon", "Mars"];

export function normalizeWeights(
  weights: Record<string, number>,
): Record<string, number> {
  const valid = criterionDefinitions.map((criterion) => ({
    id: criterion.id,
    value: Number.isFinite(weights[criterion.id]) && weights[criterion.id] >= 0
      ? weights[criterion.id]
      : criterion.defaultWeight,
  }));
  const total = valid.reduce((sum, item) => sum + item.value, 0);
  if (total <= 0) {
    const fallbackTotal = criterionDefinitions.reduce((sum, item) => sum + item.defaultWeight, 0);
    return Object.fromEntries(criterionDefinitions.map((item) => [item.id, item.defaultWeight / fallbackTotal]));
  }
  return Object.fromEntries(valid.map((item) => [item.id, item.value / total]));
}

export const defaultWeights = normalizeWeights(
  Object.fromEntries(criterionDefinitions.map((item) => [item.id, item.defaultWeight])),
);
