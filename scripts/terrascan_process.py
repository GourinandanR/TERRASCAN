#!/usr/bin/env python3
"""
TERRASCAN Stage 9 geospatial processing.
Requires Rasterio and NumPy. All outputs are derived products with JSON provenance.
No planetary CRS, units, or datum are inferred or silently substituted.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import Resampling as ResamplingEnum
from rasterio.features import geometry_mask
from rasterio.transform import xy
from rasterio.crs import CRS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "derived"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def metadata(ds):
    return {
        "driver": ds.driver, "width": ds.width, "height": ds.height,
        "count": ds.count, "dtypes": list(ds.dtypes), "crs": str(ds.crs) if ds.crs else None,
        "transform": list(ds.transform), "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
        "nodata": ds.nodata, "units": list(ds.units) if ds.units else None,
        "scales": list(ds.scales), "offsets": list(ds.offsets)
    }

def load_band(path: Path, band: int):
    with rasterio.open(path) as ds:
        if ds.crs is None:
            raise ValueError("Input raster has no CRS. Resolve its CRS from the official product label before processing.")
        if band < 1 or band > ds.count:
            raise ValueError(f"Band {band} is outside the available range 1..{ds.count}.")
        arr = ds.read(band, masked=True).astype("float64")
        # Apply GDAL/Rasterio scale and offset exactly once.
        scale = ds.scales[band - 1] if ds.scales else 1.0
        offset = ds.offsets[band - 1] if ds.offsets else 0.0
        arr = arr * scale + offset
        return arr, ds.profile.copy(), metadata(ds)

def common_grid(args):
    src = Path(args.input).resolve()
    target_crs = CRS.from_user_input(args.target_crs)
    if args.resolution <= 0:
        raise ValueError("Resolution must be a positive number in target CRS units.")
    with rasterio.open(src) as ds:
        if ds.crs is None:
            raise ValueError("Source raster has no CRS; inspect the official product label first.")
        transform, width, height = calculate_default_transform(
            ds.crs, target_crs, ds.width, ds.height, *ds.bounds, resolution=args.resolution
        )
        profile = ds.profile.copy()
        profile.update(driver="GTiff", crs=target_crs, transform=transform,
                       width=width, height=height, compress="deflate",
                       BIGTIFF="IF_SAFER")
        out = OUT / "common-grid" / f"{src.stem}_grid_{args.resolution:g}.tif"
        out.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out, "w", **profile) as dst:
            for b in range(1, ds.count + 1):
                reproject(
                    source=rasterio.band(ds, b), destination=rasterio.band(dst, b),
                    src_transform=ds.transform, src_crs=ds.crs,
                    dst_transform=transform, dst_crs=target_crs,
                    resampling=Resampling[args.resampling]
                )
        report = {
            "operation": "reproject-resample-to-explicit-grid", "createdAt": datetime.now(timezone.utc).isoformat(),
            "source": str(src), "sourceSha256": sha256(src), "sourceMetadata": metadata(ds),
            "target": str(out), "targetSha256": sha256(out), "targetCrs": target_crs.to_string(),
            "targetResolution": args.resolution, "resolutionUnits": "target CRS coordinate units",
            "resampling": args.resampling, "bandScaleOffset": "source values copied/reprojected by Rasterio; inspect source scale/offset before interpretation",
            "warning": "A common grid does not make different planetary bodies, datums, vertical references, or measurement units scientifically comparable."
        }
    write_json(out.with_suffix(".provenance.json"), report)
    print(json.dumps({"output": str(out.relative_to(ROOT)), "provenance": str(out.with_suffix(".provenance.json").relative_to(ROOT))}, indent=2))

def terrain(args):
    src = Path(args.input).resolve()
    arr, profile, meta = load_band(src, args.band)
    crs = CRS.from_user_input(meta["crs"])
    if not crs.is_projected:
        raise ValueError("Slope/aspect derivation requires a projected CRS with known linear axis units. Reproject explicitly first.")
    from pyproj import CRS as PyprojCRS
    axis_info = PyprojCRS.from_wkt(crs.to_wkt()).axis_info
    if len(axis_info) < 2 or not all(ax.unit_name.lower() in ("metre", "meter") for ax in axis_info[:2]):
        raise ValueError("This derivative implementation requires horizontal CRS axes in metres. Do not assume planetary degrees are metres.")
    units = meta.get("units") or []
    z_unit = units[args.band - 1] if len(units) >= args.band else None
    if z_unit not in ("m", "metre", "meter", "metres", "meters"):
        raise ValueError("Elevation band units are not explicitly metres. Confirm units/scale/offset from the product label before using this derivative.")
    dx = abs(profile["transform"].a)
    dy = abs(profile["transform"].e)
    if dx <= 0 or dy <= 0:
        raise ValueError("Invalid pixel dimensions.")
    data = np.asarray(arr.filled(np.nan), dtype="float64")
    valid = np.isfinite(data)
    # Nodata-safe gradients: derivatives only where center and four neighbours are valid.
    safe = np.where(valid, data, np.nan)
    dz_dy, dz_dx = np.gradient(safe, dy, dx)
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    aspect = (np.degrees(np.arctan2(-dz_dx, dz_dy)) + 360.0) % 360.0
    slope[~valid] = np.nan
    aspect[~valid] = np.nan
    base = OUT / "terrain" / src.stem
    base.parent.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, values, unit in [("slope_degrees", slope, "degree"), ("aspect_degrees", aspect, "degree")]:
        out = base.with_name(base.name + f"_{name}.tif")
        p = profile.copy()
        p.update(driver="GTiff", count=1, dtype="float32", nodata=-9999.0, compress="deflate")
        with rasterio.open(out, "w", **p) as ds:
            ds.write(np.where(np.isfinite(values), values, -9999.0).astype("float32"), 1)
            ds.set_band_description(1, name)
            ds.update_tags(1, units=unit, source_vertical_units=z_unit, algorithm="numpy.gradient central differences")
        outputs[name] = {"path": str(out), "sha256": sha256(out), "units": unit}
    report = {
        "operation": "slope-and-aspect", "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": str(src), "sourceSha256": sha256(src), "sourceMetadata": meta,
        "outputs": outputs, "pixelSizeMetres": [dx, dy],
        "method": "numpy.gradient; slope=atan(sqrt((dz/dx)^2+(dz/dy)^2)); aspect clockwise from north",
        "limitations": ["No hydrological conditioning or smoothing.", "Edge and nodata-adjacent gradients may be invalid.",
                        "Only valid for the stated projected metre CRS and metre elevation values.",
                        "Validate axis order, body-fixed frame, datum and scale/offset against the original product label."]
    }
    write_json(base.with_name(base.name + "_terrain.provenance.json"), report)
    print(json.dumps({"outputs": outputs, "status": "derived; requires scientific review"}, indent=2))

def zonal(args):
    src = Path(args.input).resolve()
    gj_path = Path(args.geojson).resolve()
    gj = json.loads(gj_path.read_text(encoding="utf-8"))
    if gj.get("type") != "FeatureCollection":
        raise ValueError("Input zones must be a GeoJSON FeatureCollection.")
    with rasterio.open(src) as ds:
        if ds.crs is None: raise ValueError("Raster CRS is missing.")
        if not args.zone_crs:
            raise ValueError("Specify --zone-crs explicitly; GeoJSON CRS defaults are not trusted for planetary data.")
        zone_crs = CRS.from_user_input(args.zone_crs)
        raster_crs = ds.crs
        if zone_crs != raster_crs:
            raise ValueError("Zone CRS must exactly match raster CRS. Reproject the GeoJSON explicitly before zonal statistics.")
        band = ds.read(args.band, masked=True).astype("float64")
        if ds.scales: band = band * ds.scales[args.band - 1]
        if ds.offsets: band = band + ds.offsets[args.band - 1]
        rows = []
        for idx, feat in enumerate(gj["features"]):
            geom = feat.get("geometry")
            if not geom: continue
            mask = geometry_mask([geom], out_shape=(ds.height, ds.width), transform=ds.transform, invert=True, all_touched=args.all_touched)
            values = band[mask].compressed()
            props = feat.get("properties") or {}
            if values.size:
                stats = {"count": int(values.size), "min": float(values.min()), "max": float(values.max()),
                         "mean": float(values.mean()), "median": float(np.median(values)), "std": float(values.std())}
            else:
                stats = {"count": 0, "min": None, "max": None, "mean": None, "median": None, "std": None}
            rows.append({"featureIndex": idx, "featureId": feat.get("id"), "properties": props, "statistics": stats})
    report = {
        "operation": "zonal-statistics", "createdAt": datetime.now(timezone.utc).isoformat(),
        "raster": str(src), "rasterSha256": sha256(src), "zones": str(gj_path), "zonesSha256": sha256(gj_path),
        "rasterCrs": str(raster_crs), "zoneCrs": str(zone_crs), "band": args.band,
        "allTouched": args.all_touched, "results": rows,
        "warning": "Statistics inherit raster band units and mask/nodata semantics. They are descriptive measurements, not analog similarity scores."
    }
    out = OUT / "site-stats" / f"{src.stem}_zonal_stats.json"
    write_json(out, report)
    print(json.dumps({"output": str(out.relative_to(ROOT)), "features": len(rows)}, indent=2))

def main():
    parser = argparse.ArgumentParser(description="TERRASCAN planetary raster processing")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("grid", help="Reproject/resample to an explicit target grid")
    p.add_argument("input"); p.add_argument("--target-crs", required=True); p.add_argument("--resolution", required=True, type=float)
    p.add_argument("--resampling", choices=["nearest","bilinear","cubic","average","mode"], default="bilinear")
    p.set_defaults(func=common_grid)
    p = sub.add_parser("terrain", help="Derive slope and aspect from a metre DEM in a projected metre CRS")
    p.add_argument("input"); p.add_argument("--band", type=int, default=1)
    p.set_defaults(func=terrain)
    p = sub.add_parser("zonal", help="Calculate descriptive statistics for GeoJSON polygons")
    p.add_argument("input"); p.add_argument("geojson"); p.add_argument("--zone-crs", required=True)
    p.add_argument("--band", type=int, default=1); p.add_argument("--all-touched", action="store_true")
    p.set_defaults(func=zonal)
    args = parser.parse_args()
    try: args.func(args)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__": main()
