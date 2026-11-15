#!/usr/bin/env python3
"""
TERRASCAN Stage 14: site-level geospatial feature extraction.

Extracts descriptive Earth-site features from explicitly prepared rasters.
It never assigns Moon/Mars target ranges, similarity scores, or mission ratings.
All output is pending scientific review and carries source hashes and metadata.
Requires rasterio, numpy, and pyproj (see requirements-geo.txt).
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.features import geometry_mask

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "derived" / "site-features"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def integral_sum(a: np.ndarray) -> np.ndarray:
    return np.pad(np.cumsum(np.cumsum(a, axis=0), axis=1), ((1, 0), (1, 0)))

def box_mean_std(values: np.ndarray, radius: int) -> tuple[np.ndarray, np.ndarray]:
    """Nodata-aware square-window mean/std via integral images."""
    valid = np.isfinite(values)
    v = np.where(valid, values, 0.0)
    pad = radius
    vp = np.pad(v, pad, mode="edge")
    mp = np.pad(valid.astype(float), pad, mode="edge")
    # Invalid edge padding is not introduced; edge values are replicated.
    def window_sum(a):
        ii = integral_sum(a)
        k = 2 * radius + 1
        return ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k]
    count = window_sum(mp)
    total = window_sum(vp)
    total2 = window_sum(vp * vp)
    mean = np.divide(total, count, out=np.full_like(total, np.nan), where=count > 0)
    variance = np.divide(total2, count, out=np.full_like(total2, np.nan), where=count > 0) - mean * mean
    std = np.sqrt(np.maximum(variance, 0))
    # Crop the padding back to the original dimensions.
    return mean, std

def open_band(path: Path, band: int, expected_unit: str):
    ds = rasterio.open(path)
    if ds.crs is None:
        ds.close()
        raise ValueError(f"{path}: CRS is missing; verify it from the official product label.")
    if not 1 <= band <= ds.count:
        ds.close()
        raise ValueError(f"{path}: band {band} outside 1..{ds.count}.")
    units = list(ds.units or [])
    unit = units[band-1] if len(units) >= band else None
    if unit != expected_unit:
        ds.close()
        raise ValueError(f"{path}: expected explicit band unit {expected_unit!r}, found {unit!r}.")
    arr = ds.read(band, masked=True).astype("float64")
    scale = ds.scales[band-1] if ds.scales else 1.0
    offset = ds.offsets[band-1] if ds.offsets else 0.0
    arr = np.asarray(arr.filled(np.nan), dtype="float64") * scale + offset
    meta = {"path": str(path), "sha256": sha256(path), "band": band, "unit": unit,
            "crs": ds.crs.to_string(), "width": ds.width, "height": ds.height,
            "transform": list(ds.transform), "scaleApplied": scale, "offsetApplied": offset}
    return ds, arr, meta

def stats(values: np.ndarray):
    x = values[np.isfinite(values)]
    if x.size == 0:
        return {"count": 0, "min": None, "max": None, "mean": None, "std": None,
                "median": None, "p90": None}
    return {"count": int(x.size), "min": float(x.min()), "max": float(x.max()),
            "mean": float(x.mean()), "std": float(x.std()),
            "median": float(np.median(x)), "p90": float(np.percentile(x, 90))}

def extract(args):
    zones_path = Path(args.geojson).resolve()
    zones = json.loads(zones_path.read_text(encoding="utf-8"))
    if zones.get("type") != "FeatureCollection":
        raise ValueError("Zones input must be a GeoJSON FeatureCollection.")
    if not args.zone_crs:
        raise ValueError("Explicit --zone-crs is required; GeoJSON CRS is not assumed.")
    zone_crs = CRS.from_user_input(args.zone_crs)
    dem_path, slope_path, thermal_path, geology_path = map(
        lambda x: Path(x).resolve(), (args.dem, args.slope, args.thermal, args.geology))
    opened = []
    try:
        dem_ds, dem, dem_meta = open_band(dem_path, args.dem_band, "m"); opened.append(dem_ds)
        slope_ds, slope, slope_meta = open_band(slope_path, args.slope_band, "degree"); opened.append(slope_ds)
        thermal_ds, thermal, thermal_meta = open_band(thermal_path, args.thermal_band, "K"); opened.append(thermal_ds)
        geology_ds = rasterio.open(geology_path); opened.append(geology_ds)
        if geology_ds.crs is None: raise ValueError("Geology raster CRS is missing.")
        if zone_crs != dem_ds.crs: raise ValueError("Zone CRS must exactly match DEM CRS; reproject zones explicitly.")
        for name, ds in (("slope", slope_ds), ("thermal", thermal_ds), ("geology", geology_ds)):
            if ds.crs != dem_ds.crs:
                raise ValueError(f"{name} raster CRS differs from DEM CRS. Regrid explicitly before extraction.")
            if ds.transform != dem_ds.transform or ds.width != dem_ds.width or ds.height != dem_ds.height:
                raise ValueError(f"{name} raster grid differs from DEM. Use Stage 9 common-grid processing first.")
        if not args.site_id_field:
            raise ValueError("--site-id-field is required to identify each candidate site.")
        classes = json.loads(Path(args.geology_classes).read_text(encoding="utf-8"))
        # Keys in the class dictionary are exact raster integer values.
        geology = geology_ds.read(args.geology_band, masked=True).astype("float64").filled(np.nan)
        geology = np.asarray(geology, dtype="float64")
        _, roughness = box_mean_std(dem, args.roughness_radius)
        sources = {"elevation": dem_meta, "slope": slope_meta, "thermal": thermal_meta,
                   "geology": {"path": str(geology_path), "sha256": sha256(geology_path),
                               "band": args.geology_band, "unit": "categorical",
                               "crs": geology_ds.crs.to_string(), "width": geology_ds.width,
                               "height": geology_ds.height, "transform": list(geology_ds.transform)}}
        results = []
        seen = set()
        for index, feature in enumerate(zones.get("features", [])):
            props = feature.get("properties") or {}
            site_id = str(props.get(args.site_id_field, "")).strip()
            if not site_id: raise ValueError(f"Feature {index} has no {args.site_id_field!r} property.")
            if site_id in seen: raise ValueError(f"Duplicate site ID {site_id!r}.")
            seen.add(site_id)
            geom = feature.get("geometry")
            if not geom: raise ValueError(f"Feature {index} has no geometry.")
            mask = geometry_mask([geom], out_shape=(dem_ds.height, dem_ds.width),
                                 transform=dem_ds.transform, invert=True, all_touched=args.all_touched)
            dem_s, slope_s, rough_s, thermal_s = (a[mask] for a in (dem, slope, roughness, thermal))
            geo_s = geology[mask]
            valid_geo = geo_s[np.isfinite(geo_s)]
            counts = {}
            for val in valid_geo:
                key = str(int(val)) if float(val).is_integer() else str(val)
                counts[key] = counts.get(key, 0) + 1
            dominant = max(counts, key=counts.get) if counts else None
            geology_name = classes.get(dominant) if dominant is not None else None
            if dominant is not None and geology_name is None:
                raise ValueError(f"Unmapped geology class {dominant!r}; add it to --geology-classes JSON.")
            features_out = {
                "slope": {"value": stats(slope_s)["mean"], "unit": "degree", "summary": stats(slope_s)},
                "roughness": {"value": stats(rough_s)["mean"], "unit": "m",
                              "summary": stats(rough_s), "method": f"local elevation standard deviation, square radius {args.roughness_radius} pixels"},
                "thermal": {"value": stats(thermal_s)["mean"], "unit": "K", "summary": stats(thermal_s)},
                "elevationRange": {"value": (float(np.nanmax(dem_s)-np.nanmin(dem_s)) if np.isfinite(dem_s).any() else None),
                                   "unit": "m", "summary": stats(dem_s)},
                "geology": {"value": geology_name, "classValue": dominant, "unit": "class",
                            "classCounts": counts, "validPixelCount": int(valid_geo.size)}
            }
            for key, item in features_out.items():
                item["status"] = "derived-pending-review" if item.get("value") is not None else "no-valid-pixels"
            results.append({"siteId": site_id, "properties": props, "features": features_out})
        report = {
            "schemaVersion": "1.0", "stage": 14, "operation": "site-feature-extraction",
            "createdAt": datetime.now(timezone.utc).isoformat(), "status": "pending-human-review",
            "planetaryBody": "Earth", "zoneSource": {"path": str(zones_path), "sha256": sha256(zones_path),
                                                        "crs": zone_crs.to_string()},
            "sources": sources, "parameters": {"roughnessRadiusPixels": args.roughness_radius,
                                                  "allTouched": args.all_touched,
                                                  "siteIdField": args.site_id_field},
            "sites": results,
            "limitations": [
                "This tool extracts descriptive features for Earth analog candidates only.",
                "It does not create Moon/Mars target reference ranges or calculate similarity scores.",
                "Roughness is the local standard deviation of DEM elevation, not a universal geomorphic roughness metric.",
                "Slope raster must be produced by the validated Stage 9 terrain workflow.",
                "All rasters must already share exactly the same CRS, dimensions and affine transform.",
                "Thermal band must be explicitly in Kelvin; temporal context and acquisition comparability require separate review.",
                "Geology class labels must be sourced from an authoritative legend and reviewed.",
                "Outputs are pending human review and must not be inserted as approved evidence automatically."
            ]
        }
        OUT.mkdir(parents=True, exist_ok=True)
        output = OUT / f"{args.output_name}.features.json"
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {output}; use --overwrite intentionally.")
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"output": str(output), "sha256": sha256(output),
                          "sites": len(results), "status": report["status"]}, indent=2))
    finally:
        for ds in opened: ds.close()

def main():
    parser = argparse.ArgumentParser(description="TERRASCAN Stage 14 geospatial feature extraction")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract", help="Extract candidate-site features from aligned raster inputs")
    p.add_argument("--dem", required=True); p.add_argument("--slope", required=True)
    p.add_argument("--thermal", required=True); p.add_argument("--geology", required=True)
    p.add_argument("--geojson", required=True); p.add_argument("--zone-crs", required=True)
    p.add_argument("--site-id-field", required=True); p.add_argument("--geology-classes", required=True)
    p.add_argument("--dem-band", type=int, default=1); p.add_argument("--slope-band", type=int, default=1)
    p.add_argument("--thermal-band", type=int, default=1); p.add_argument("--geology-band", type=int, default=1)
    p.add_argument("--roughness-radius", type=int, default=1)
    p.add_argument("--all-touched", action="store_true"); p.add_argument("--output-name", default="earth-analog-sites")
    p.add_argument("--overwrite", action="store_true"); p.set_defaults(func=extract)
    args = parser.parse_args()
    try:
        if args.roughness_radius < 1 or args.roughness_radius > 50:
            raise ValueError("--roughness-radius must be between 1 and 50 pixels.")
        args.func(args)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr); sys.exit(1)
if __name__ == "__main__": main()
