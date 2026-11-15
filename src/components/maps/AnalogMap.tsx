import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { Map as MapLibreMap } from "maplibre-gl";
import { analogSites } from "../../data/analogSites";

maplibregl.setWorkerUrl(workerUrl);

type Props = {
  selectedSiteId: string | null;
  showCandidates: boolean;
  onSelectSite: (id: string) => void;
};

const sourceId = "terrascan-candidates";
const layerId = "terrascan-candidate-points";

export default function AnalogMap({ selectedSiteId, showCandidates, onSelectSite }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const onSelectRef = useRef(onSelectSite);
  onSelectRef.current = onSelectSite;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          "osm-raster": {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            minzoom: 0,
            maxzoom: 19,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm-raster-layer", type: "raster", source: "osm-raster" }],
      },
      center: [8, 18],
      zoom: 1.15,
      minZoom: 1,
      maxZoom: 15,
      renderWorldCopies: false,
      attributionControl: {},
    });

    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 100, unit: "metric" }), "bottom-left");

    map.on("load", () => {
      map.addSource(sourceId, {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: analogSites.map((site) => ({
            type: "Feature" as const,
            properties: { id: site.id, name: site.name },
            geometry: { type: "Point" as const, coordinates: site.coordinates },
          })),
        },
      });

      map.addLayer({
        id: layerId,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-radius": [
            "case",
            ["==", ["get", "id"], selectedSiteId ?? ""], 9,
            6,
          ],
          "circle-color": "#39d2df",
          "circle-stroke-color": "#e7fbff",
          "circle-stroke-width": 1.7,
          "circle-opacity": 0.95,
          "circle-blur": 0.08,
        },
      });

      map.addLayer({
        id: "terrascan-candidate-halo",
        type: "circle",
        source: sourceId,
        paint: {
          "circle-radius": 13,
          "circle-color": "#39d2df",
          "circle-opacity": 0.13,
        },
      }, layerId);

      map.on("click", layerId, (event) => {
        const feature = event.features?.[0];
        const id = feature?.properties?.id;
        if (typeof id === "string") onSelectRef.current(id);
      });
      map.on("mouseenter", layerId, () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", layerId, () => { map.getCanvas().style.cursor = ""; });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const update = () => {
      if (map.getLayer(layerId)) {
        map.setPaintProperty(layerId, "circle-radius", [
          "case", ["==", ["get", "id"], selectedSiteId ?? ""], 9, 6,
        ]);
        map.setLayoutProperty(layerId, "visibility", showCandidates ? "visible" : "none");
        if (map.getLayer("terrascan-candidate-halo")) {
          map.setLayoutProperty("terrascan-candidate-halo", "visibility", showCandidates ? "visible" : "none");
        }
      }
    };
    if (map.isStyleLoaded()) update();
    else map.once("load", update);
  }, [selectedSiteId, showCandidates]);

  useEffect(() => {
    const map = mapRef.current;
    const site = analogSites.find((item) => item.id === selectedSiteId);
    if (!map || !site) return;
    map.flyTo({ center: site.coordinates, zoom: Math.max(map.getZoom(), 3.1), duration: 900, essential: true });
  }, [selectedSiteId]);

  return <div ref={containerRef} className="maplibre-canvas" aria-label="Interactive map showing terrestrial analog research candidates" />;
}
