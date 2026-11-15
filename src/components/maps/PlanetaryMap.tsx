import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { PlanetaryBody, PlanetaryLayerKey } from "../../data/planetaryLayers";
import { planetaryLayers } from "../../data/planetaryLayers";

maplibregl.setWorkerUrl(workerUrl);
maplibregl.addProjection({
  name: "terrascan:planetary-geographic",
  projection: {
    forward: ([longitude, latitude]) => [longitude, latitude],
    inverse: ([x, y]) => [x, y],
  },
  tileMatrixSet: { origin: [-180, 180], extentAtZoom0: 360 },
});

type Props = {
  body: Exclude<PlanetaryBody, "Earth">;
  layerKey: PlanetaryLayerKey;
};

const WMS_ENDPOINT = "https://planetarymaps.usgs.gov/cgi-bin/mapserv";
const sourceId = "terrascan-planetary-wms";
const rasterLayerId = "terrascan-planetary-raster";

function wmsTemplate(mapFile: string, layer: string) {
  const params = [
    "SERVICE=WMS",
    "VERSION=1.1.1",
    "REQUEST=GetMap",
    `MAP=${encodeURIComponent(mapFile)}`,
    `LAYERS=${encodeURIComponent(layer)}`,
    "STYLES=",
    "SRS=EPSG%3A4326",
    "BBOX={bbox}",
    "WIDTH=256",
    "HEIGHT=256",
    "FORMAT=image%2Fpng",
    "TRANSPARENT=false",
  ].join("&");
  return `${WMS_ENDPOINT}?${params}`;
}

export default function PlanetaryMap({ body, layerKey }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const initialLayer = planetaryLayers[body][layerKey];
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        projection: { type: "terrascan:planetary-geographic" },
        sources: {
          [sourceId]: {
            type: "raster",
            tiles: [wmsTemplate(initialLayer.mapFile!, initialLayer.wmsLayer!)],
            tileSize: 256,
            minzoom: 0,
            maxzoom: 8,
            attribution: initialLayer.attribution,
          },
        },
        layers: [
          { id: "planetary-background", type: "background", paint: { "background-color": "#101a24" } },
          { id: rasterLayerId, type: "raster", source: sourceId, paint: { "raster-opacity": 1 } },
        ],
      },
      center: [0, 0],
      zoom: 0.1,
      minZoom: 0,
      maxZoom: 7,
      renderWorldCopies: false,
      attributionControl: {},
    });

    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
    map.on("error", (event) => {
      const message = event.error?.message ?? "The planetary map service returned an error.";
      setMapError(message);
    });
    map.on("idle", () => setMapError(null));

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource(sourceId)) return;
    const next = planetaryLayers[body][layerKey];
    const source = map.getSource(sourceId) as { setTiles: (tiles: string[]) => void } | undefined;
    source?.setTiles([wmsTemplate(next.mapFile!, next.wmsLayer!)]);
    map.setCenter([0, 0]);
    map.setZoom(0.1);
    setMapError(null);
  }, [body, layerKey]);

  return (
    <div className="planetary-map-frame">
      <div ref={containerRef} className="maplibre-canvas" aria-label={`${body} planetary basemap`} />
      <div className="map-overlay-chip"><span className="status-dot"/> USGS ASTRO WEB MAPS · {body.toUpperCase()}</div>
      {mapError && <div className="map-service-warning"><strong>Map service response</strong><span>{mapError}</span><small>The layer catalog entry is retained below so the source can still be opened directly.</small></div>}
    </div>
  );
}
