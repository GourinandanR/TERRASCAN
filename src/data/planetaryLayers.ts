export type PlanetaryBody = "Earth" | "Moon" | "Mars";
export type PlanetaryLayerKey = "imagery" | "topography";

export type PlanetaryLayer = {
  key: PlanetaryLayerKey;
  label: string;
  description: string;
  service: "earth-osm" | "usgs-wms";
  mapFile?: string;
  wmsLayer?: string;
  attribution: string;
  sourceName: string;
  sourceUrl: string;
  projection: string;
  dataNotes: string;
};

export const planetaryLayers: Record<Exclude<PlanetaryBody, "Earth">, Record<PlanetaryLayerKey, PlanetaryLayer>> = {
  Moon: {
    imagery: {
      key: "imagery",
      label: "LROC Wide Angle Camera",
      description: "Global lunar image mosaic",
      service: "usgs-wms",
      mapFile: "/maps/earth/moon_simp_cyl.map",
      wmsLayer: "LROC_WAC",
      attribution: "USGS Astrogeology · ASU / NASA",
      sourceName: "USGS Astro Web Maps — LROC WAC",
      sourceUrl: "https://astrowebmaps.wr.usgs.gov/webmapatlas/Layers/maps.html",
      projection: "Simple cylindrical / geographic longitude-latitude",
      dataNotes: "Global lunar mosaic layer listed in the USGS Astro Web Maps catalog.",
    },
    topography: {
      key: "topography",
      label: "LOLA Color Shaded Relief",
      description: "Lunar elevation-derived shaded relief visualization",
      service: "usgs-wms",
      mapFile: "/maps/earth/moon_simp_cyl.map",
      wmsLayer: "LOLA_color",
      attribution: "Goddard Space Flight Center / NASA",
      sourceName: "USGS Astro Web Maps — LROC LOLA Color Shade",
      sourceUrl: "https://astrowebmaps.wr.usgs.gov/webmapatlas/Layers/maps.html",
      projection: "Simple cylindrical / geographic longitude-latitude",
      dataNotes: "Catalogued LOLA color-shade visualization. This is a rendered browse layer, not a raw elevation raster for quantitative analysis.",
    },
  },
  Mars: {
    imagery: {
      key: "imagery",
      label: "MOLA–THEMIS Blend",
      description: "Global Mars shaded-relief and thermal-infrared blend",
      service: "usgs-wms",
      mapFile: "/maps/mars/mars_simp_cyl.map",
      wmsLayer: "MOLA_THEMIS_blend",
      attribution: "Goddard Space Flight Center / ASU / USGS",
      sourceName: "USGS Astro Web Maps — MOLA THEMIS Blend",
      sourceUrl: "https://astrowebmaps.wr.usgs.gov/webmapatlas/Layers/maps.html",
      projection: "Simple cylindrical / geographic longitude-latitude",
      dataNotes: "Global Mars layer listed in the USGS Astro Web Maps catalog.",
    },
    topography: {
      key: "topography",
      label: "MOLA Color Elevation",
      description: "Mars elevation visualization from MOLA",
      service: "usgs-wms",
      mapFile: "/maps/mars/mars_simp_cyl.map",
      wmsLayer: "MOLA_color",
      attribution: "Goddard Space Flight Center / USGS",
      sourceName: "USGS Astro Web Maps — MOLA Color",
      sourceUrl: "https://astrowebmaps.wr.usgs.gov/webmapatlas/Layers/maps.html",
      projection: "Simple cylindrical / geographic longitude-latitude",
      dataNotes: "Rendered global colorized MOLA browse layer. Use the PDS archive or analysis-ready elevation products for scientific measurements.",
    },
  },
};

export const planetaryDataResources = [
  {
    body: "Moon",
    title: "LOLA — Lunar Orbiter Laser Altimeter",
    role: "Lunar global topography data archive",
    organization: "NASA / Planetary Data System",
    url: "https://pds-geosciences.wustl.edu/missions/lro/lola.htm",
    status: "Catalogued archive",
  },
  {
    body: "Moon",
    title: "Lunar Polar Illumination Products",
    role: "Polar illumination products with GeoTIFF and Cloud-Optimized GeoTIFF options",
    organization: "NASA Goddard / LOLA",
    url: "https://pgda.gsfc.nasa.gov/products/69",
    status: "Product page",
  },
  {
    body: "Mars",
    title: "Mars Global Data Sets — MOLA",
    role: "Global shaded relief and colorized elevation browse products",
    organization: "Arizona State University",
    url: "https://www.mars.asu.edu/data/",
    status: "Data catalog",
  },
  {
    body: "Earth",
    title: "NASA Global Imagery Browse Services",
    role: "Earth-observation visualization services (WMTS / WMS / TMS)",
    organization: "NASA Earthdata",
    url: "https://nasa-gibs.github.io/gibs-api-docs/",
    status: "Service documentation",
  },
  {
    body: "All",
    title: "USGS Astrogeology Data & Tools",
    role: "Planetary basemaps, image archives, processing and analysis-ready data",
    organization: "USGS Astrogeology Science Center",
    url: "https://www.usgs.gov/centers/astrogeology-science-center/data",
    status: "Data portal",
  },
] as const;
