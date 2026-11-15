#!/usr/bin/env python3
"""TERRASCAN Stage 23: multiscale planetary terrain and spatial metrics.

Requires Rasterio, NumPy and SciPy. This tool computes descriptive raster metrics
only; it does not identify analog sites, infer units, or approve evidence.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "spatial-analysis"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def write_immutable(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing analysis: {path}")
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")

def require_validation(path: Path, body: str) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    if str(report.get("expectedBody", "")).lower() != body.lower():
        raise ValueError("Validation report body does not match --body; cross-body analysis is blocked.")
    summary = report.get("summary") or {}
    if summary.get("fail", 0):
        raise ValueError("Stage 22 validation contains failed checks; resolve them before spatial analysis.")
    return report

def window_metrics(data: np.ndarray, valid: np.ndarray, size: int):
    # Normalized local means respect nodata; metrics are emitted only where the
    # complete neighborhood is valid, avoiding partial-window edge artefacts.
    weights = valid.astype(np.float64)
    count = uniform_filter(weights, size=size, mode="constant", cval=0.0) * (size * size)
    total = uniform_filter(np.where(valid, data, 0.0), size=size, mode="constant", cval=0.0) * (size * size)
    mean = np.divide(total, count, out=np.full_like(total, np.nan), where=count > 0)
    total2 = uniform_filter(np.where(valid, data * data, 0.0), size=size, mode="constant", cval=0.0) * (size * size)
    variance = np.maximum(np.divide(total2, count, out=np.full_like(total2, np.nan), where=count > 0) - mean * mean, 0)
    std = np.sqrt(variance)
    complete = (count >= size * size - 1e-6)
    tpi = data - mean
    tpi[~complete] = np.nan
    std[~complete] = np.nan
    # Terrain ruggedness index: RMS difference from neighborhood mean is a
    # local relief proxy, not a geomorphological classification.
    tri = np.sqrt(variance)
    tri[~complete] = np.nan
    return tpi, tri, std, complete

def summarize(values: np.ndarray) -> dict:
    x = values[np.isfinite(values)]
    if not x.size:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "std": None,
                "p05": None, "p25": None, "p75": None, "p95": None}
    q = np.percentile(x, [5,25,50,75,95])
    return {"count": int(x.size), "min": float(x.min()), "max": float(x.max()),
            "mean": float(x.mean()), "median": float(q[2]), "std": float(x.std()),
            "p05": float(q[0]), "p25": float(q[1]), "p75": float(q[3]), "p95": float(q[4])}

def run(args) -> dict:
    src = Path(args.input).resolve()
    validation_path = Path(args.validation_report).resolve()
    validation = require_validation(validation_path, args.body)
    with rasterio.open(src) as ds:
        if ds.crs is None:
            raise ValueError("Raster CRS is missing; Stage 22 validation must establish a declared CRS.")
        if not 1 <= args.band <= ds.count:
            raise ValueError(f"Band must be within 1..{ds.count}.")
        if ds.transform.a == 0 or ds.transform.e == 0 or ds.transform.b != 0 or ds.transform.d != 0:
            raise ValueError("Rotated or degenerate grids are unsupported; warp explicitly to a north-up grid first.")
        if not args.pixel_size_units:
            raise ValueError("Supply --pixel-size-units from authoritative product documentation (e.g. m or km).")
        if args.pixel_size_units not in ("m", "km", "degree"):
            raise ValueError("--pixel-size-units must be m, km, or degree.")
        arr = ds.read(args.band, masked=True).astype("float64")
        scale = ds.scales[args.band - 1] if ds.scales else 1.0
        offset = ds.offsets[args.band - 1] if ds.offsets else 0.0
        data = np.asarray(arr.filled(np.nan), dtype=np.float64) * scale + offset
        valid = np.isfinite(data)
        if valid.sum() < 25:
            raise ValueError("At least 25 valid pixels are required for neighborhood analysis.")
        pixel_x, pixel_y = abs(ds.transform.a), abs(ds.transform.e)
        meta = {"width": ds.width, "height": ds.height, "crs": ds.crs.to_string(),
                "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
                "pixelSize": [pixel_x, pixel_y], "pixelSizeUnits": args.pixel_size_units,
                "band": args.band, "bandUnit": ds.units[args.band - 1] if ds.units else None,
                "scale": scale, "offset": offset, "nodata": ds.nodata}
    scales = []
    for size in args.windows:
        if size < 3 or size % 2 == 0:
            raise ValueError("Neighborhood window sizes must be odd integers >= 3.")
        if size > min(data.shape):
            raise ValueError(f"Window {size} exceeds raster dimensions.")
        tpi, tri, local_std, complete = window_metrics(data, valid, size)
        scales.append({"windowPixels": size, "windowApproxSize": [size*pixel_x, size*pixel_y],
                       "windowUnits": args.pixel_size_units,
                       "validCenterCount": int(complete.sum()),
                       "topographicPositionIndex": summarize(tpi),
                       "terrainRuggednessProxy": summarize(tri),
                       "localElevationStdDev": summarize(local_std),
                       "interpretation": "Descriptive neighborhood statistics; not a landform class or mission-suitability score."})
    report = {
        "schemaVersion": "1.0", "analysis": "multiscale-planetary-raster-descriptives",
        "generatedAt": datetime.now(timezone.utc).isoformat(), "body": args.body,
        "source": str(src), "sourceSha256": sha256(src), "sourceMetadata": meta,
        "validationReport": str(validation_path), "validationReportSha256": sha256(validation_path),
        "validationOverall": (validation.get("summary") or {}).get("overall"),
        "validPixelCount": int(valid.sum()), "invalidPixelCount": int((~valid).sum()),
        "valueStatistics": summarize(data[valid]), "scales": scales,
        "scientificDisposition": "descriptive-only-pending-human-review",
        "evidenceApproval": "unchanged", "similarityScores": "not-computed",
        "limitations": [
            "Pixel spacing units are supplied by the operator and must be checked against the authoritative product label.",
            "Neighborhood windows are measured in pixels; approximate ground dimensions assume the supplied spacing is meaningful and locally applicable.",
            "TPI and local standard deviation are scale-dependent descriptive metrics, not validated geomorphological classifications.",
            "No latitude-dependent distortion correction, planetary curvature correction, vertical datum conversion or cross-body comparison is performed.",
            "No values are inferred for no-data pixels; incomplete neighborhood windows are excluded.",
            "A Stage 22 report without failures may still contain unknown checks and does not constitute scientific approval."
        ]
    }
    out = Path(args.output).resolve() if args.output else OUT / f"{src.stem}-{args.body.lower()}-spatial-analysis.json"
    write_immutable(out, report)
    return {"report": str(out), "sha256": sha256(out), "validPixels": int(valid.sum()),
            "scales": len(scales), "validationOverall": report["validationOverall"],
            "scientificDisposition": report["scientificDisposition"]}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="Validated raster file")
    ap.add_argument("--validation-report", required=True, help="Stage 22 JSON validation report")
    ap.add_argument("--body", required=True, choices=["Earth", "Moon", "Mars"])
    ap.add_argument("--band", type=int, default=1)
    ap.add_argument("--windows", type=int, nargs="+", default=[3, 7, 15])
    ap.add_argument("--pixel-size-units", required=True, choices=["m", "km", "degree"])
    ap.add_argument("--output")
    args = ap.parse_args()
    try:
        print(json.dumps(run(args), indent=2))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
