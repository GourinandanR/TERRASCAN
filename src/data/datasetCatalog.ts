export type DatasetStatus = "catalogued" | "metadata-reviewed" | "download-pending" | "ingested" | "validated";

export type DatasetRecord = {
  id: string;
  target: "Moon" | "Mars" | "Earth";
  criterion: "terrain" | "thermal" | "geology" | "resources" | "atmosphere" | "radiation" | "operations";
  title: string;
  instrument: string;
  provider: string;
  landingPage: string;
  accessUrl: string;
  productType: string;
  knownResolution: string;
  units: string;
  coordinateReference: string;
  spatialCoverage: string;
  temporalCoverage: string;
  caveats: string[];
  status: DatasetStatus;
};

export const datasetCatalog: DatasetRecord[] = [
  {
    id: "moon-lola-dem",
    target: "Moon",
    criterion: "terrain",
    title: "Lunar Orbiter Laser Altimeter (LOLA) archive and derived DEMs",
    instrument: "LOLA / Lunar Reconnaissance Orbiter",
    provider: "NASA Planetary Data System; LOLA node at MIT",
    landingPage: "https://imbrium.mit.edu/",
    accessUrl: "https://pds-geosciences.wustl.edu/missions/lro/lola.htm",
    productType: "PDS archive; gridded topography and regional DEM products",
    knownResolution: "Product-dependent; regional products include 5 m/pixel near the lunar south pole",
    units: "Elevation units and scale must be read from each product label",
    coordinateReference: "Product-specific lunar reference frame and map projection; inspect PDS labels",
    spatialCoverage: "Global archive plus selected high-resolution polar DEMs",
    temporalCoverage: "LRO mission observations; product-specific acquisition coverage",
    caveats: [
      "Do not assume all products share resolution, projection, vertical datum or processing version.",
      "The 5 m/pixel south-pole DEM is regional, not a global product.",
      "Read the PDS label and ancillary metadata before ingestion.",
    ],
    status: "catalogued",
  },
  {
    id: "mars-mola-megdr",
    target: "Mars",
    criterion: "terrain",
    title: "MOLA Mission Experiment Gridded Data Records (MEGDR)",
    instrument: "MOLA / Mars Global Surveyor",
    provider: "NASA Planetary Data System Geosciences Node",
    landingPage: "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html",
    accessUrl: "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html",
    productType: "Global gridded altimetry-derived topographic maps",
    knownResolution: "4, 16, 32, 64 and 128 pixels/degree; polar products 128, 256 and 512 pixels/degree",
    units: "Product-specific radius, areoid and topography values; inspect PDS labels",
    coordinateReference: "Final Version L products use IAU 2000; older products may use IAU 1991",
    spatialCoverage: "Global Mars and dedicated polar maps",
    temporalCoverage: "Accumulated MGS MOLA mission altimetry",
    caveats: [
      "MEGDR products include different map layers: radius, areoid (not present in every resolution), topography and observation counts.",
      "Preserve the product version and coordinate-system realization.",
      "Use PDS4 labels and accompanying ENVI headers when interpreting image files.",
    ],
    status: "catalogued",
  },
  {
    id: "mars-themis-global-ir",
    target: "Mars",
    criterion: "thermal",
    title: "THEMIS global daytime and nighttime infrared mosaics",
    instrument: "THEMIS / Mars Odyssey",
    provider: "Arizona State University Mars Space Flight Facility",
    landingPage: "https://mars.asu.edu/data/",
    accessUrl: "https://mars.asu.edu/data/",
    productType: "Global thermal-infrared mosaics",
    knownResolution: "Listed products include 100 m (593 pixels/degree) and 230 m (256 pixels/degree)",
    units: "Radiance/temperature interpretation is product-specific; inspect documentation and labels",
    coordinateReference: "Product metadata must be inspected before reprojection",
    spatialCoverage: "Global Mars mosaics",
    temporalCoverage: "Composite products; constituent image acquisition periods must be checked",
    caveats: [
      "A mosaic is not a single-time surface temperature measurement.",
      "Day and night products must not be mixed without recording local-time and seasonal context.",
      "Check calibration, photometric processing, seam handling and metadata before deriving temperature.",
    ],
    status: "catalogued",
  },
  {
    id: "mars-tes-thermal-inertia",
    target: "Mars",
    criterion: "thermal",
    title: "TES thermal inertia global products",
    instrument: "TES / Mars Global Surveyor",
    provider: "Arizona State University Mars Space Flight Facility",
    landingPage: "https://mars.asu.edu/data/",
    accessUrl: "https://mars.asu.edu/data/",
    productType: "Global derived thermal-inertia maps",
    knownResolution: "Catalogued products include 7.5 km and 3 km grids",
    units: "Thermal inertia; confirm units and scaling in product documentation",
    coordinateReference: "Product-specific map projection; inspect files and labels",
    spatialCoverage: "Global Mars",
    temporalCoverage: "Derived from MGS TES observations; product-specific",
    caveats: [
      "Thermal inertia is a derived surface property, not direct surface temperature.",
      "Products differ in temporal sampling, model assumptions and spatial resolution.",
      "Do not mix products without harmonizing definitions and units.",
    ],
    status: "catalogued",
  },
  {
    id: "mars-global-geology",
    target: "Mars",
    criterion: "geology",
    title: "Mars global geology map and supporting map products",
    instrument: "Compiled orbital geology mapping",
    provider: "NASA Ames Marsoweb archive",
    landingPage: "https://marsoweb.nas.nasa.gov/globalData/",
    accessUrl: "https://marsoweb.nas.nasa.gov/globalData/datamaps.html",
    productType: "Global geology map browse product",
    knownResolution: "Browse image dimensions are published; map scale and source-unit resolution require product documentation",
    units: "Categorical geologic units; legend and taxonomy required",
    coordinateReference: "Global map projection; inspect original file and legend",
    spatialCoverage: "Global Mars",
    temporalCoverage: "Compilation vintage; confirm in accompanying documentation",
    caveats: [
      "The archive page describes geology imagery composited with MOLA shaded relief for orientation.",
      "Do not treat the composite as a georeferenced analysis raster without source files and map metadata.",
      "Geologic unit taxonomy must be mapped to an explicit, reviewed classification before categorical scoring.",
    ],
    status: "catalogued",
  },
];

export const datasetStatusLabel: Record<DatasetStatus, string> = {
  catalogued: "Catalogued · not downloaded",
  "metadata-reviewed": "Metadata reviewed",
  "download-pending": "Download pending",
  ingested: "Ingested",
  validated: "Validated",
};
