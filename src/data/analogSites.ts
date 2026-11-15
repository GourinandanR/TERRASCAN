export type AnalogSite = {
  id: string;
  name: string;
  region: string;
  country: string;
  coordinates: [number, number]; // [longitude, latitude], approximate locator only
  analogFocus: string;
  status: "Candidate";
  note: string;
};

export const analogSites: AnalogSite[] = [
  {
    id: "atacama",
    name: "Atacama Desert",
    region: "Northern Chile",
    country: "Chile",
    coordinates: [-69.25, -24.5],
    analogFocus: "Hyper-arid desert environments",
    status: "Candidate",
    note: "Initial research candidate. Site-level geological and environmental measurements have not yet been assessed.",
  },
  {
    id: "mcmurdo",
    name: "McMurdo Dry Valleys",
    region: "Victoria Land, Antarctica",
    country: "Antarctica",
    coordinates: [161.9, -77.5],
    analogFocus: "Cold desert and exposed polar terrain",
    status: "Candidate",
    note: "Initial research candidate. The locator represents the wider Dry Valleys region, not a surveyed boundary.",
  },
  {
    id: "death-valley",
    name: "Death Valley",
    region: "California / Nevada",
    country: "United States",
    coordinates: [-116.85, 36.24],
    analogFocus: "Arid basin and rugged desert terrain",
    status: "Candidate",
    note: "Initial research candidate. Local conditions vary substantially across the valley.",
  },
  {
    id: "haughton",
    name: "Haughton Crater",
    region: "Devon Island, Nunavut",
    country: "Canada",
    coordinates: [-89.68, 75.37],
    analogFocus: "Impact-crater geology and polar desert",
    status: "Candidate",
    note: "Initial research candidate. The marker is an approximate crater-area locator.",
  },
  {
    id: "iceland",
    name: "Icelandic volcanic landscapes",
    region: "Iceland",
    country: "Iceland",
    coordinates: [-18.7, 64.9],
    analogFocus: "Volcanic and basaltic terrain",
    status: "Candidate",
    note: "Broad regional candidate. Individual volcanic sites must be selected before scientific comparison.",
  },
];
