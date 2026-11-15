#!/usr/bin/env python3
"""TERRASCAN Stage 24: transparent, configuration-driven surface feature classification.

This is a deterministic rule engine, not a trained model or scientific landform
classifier. All thresholds and class names must be supplied and reviewed by users.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "surface-classification"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def immutable_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): raise FileExistsError(f"Refusing to overwrite: {path}")
    path.write_text(json.dumps(payload,indent=2,allow_nan=False),encoding="utf-8")

def load_config(path: Path) -> dict:
    cfg=json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schemaVersion")!="1.0" or not isinstance(cfg.get("classes"),list) or not cfg["classes"]:
        raise ValueError("Config requires schemaVersion '1.0' and a non-empty classes array.")
    seen=set()
    for item in cfg["classes"]:
        if not isinstance(item,dict) or not isinstance(item.get("name"),str) or not item["name"].strip():
            raise ValueError("Each class needs a non-empty name.")
        if item["name"] in seen: raise ValueError("Class names must be unique.")
        seen.add(item["name"])
        for key in ("slopeDegrees","tpi","localStdDev"):
            bounds=item.get(key)
            if not isinstance(bounds,list) or len(bounds)!=2:
                raise ValueError(f"Class {item['name']} requires [{key}] [minimum, maximum].")
            lo,hi=bounds
            if lo is not None and not math.isfinite(float(lo)): raise ValueError(f"Invalid lower bound for {key}.")
            if hi is not None and not math.isfinite(float(hi)): raise ValueError(f"Invalid upper bound for {key}.")
            if lo is not None and hi is not None and float(lo)>float(hi): raise ValueError(f"Reversed range for {key}.")
    return cfg

def require_validation(path: Path, body: str):
    v=json.loads(path.read_text(encoding="utf-8"))
    if str(v.get("expectedBody","")).lower()!=body.lower():
        raise ValueError("Stage 22 validation report body mismatch.")
    summary=v.get("summary") or {}
    if summary.get("fail",0): raise ValueError("Stage 22 validation has failed checks; classification blocked.")
    return v

def neighborhood(data, valid, window):
    n=window*window
    weights=valid.astype(float)
    count=uniform_filter(weights,size=window,mode="constant",cval=0)*n
    sums=uniform_filter(np.where(valid,data,0),size=window,mode="constant",cval=0)*n
    sums2=uniform_filter(np.where(valid,data*data,0),size=window,mode="constant",cval=0)*n
    mean=np.divide(sums,count,out=np.full_like(sums,np.nan),where=count>0)
    var=np.maximum(np.divide(sums2,count,out=np.full_like(sums2,np.nan),where=count>0)-mean*mean,0)
    complete=count>=n-1e-6
    tpi=data-mean
    std=np.sqrt(var)
    tpi[~complete]=np.nan; std[~complete]=np.nan
    return tpi,std,complete

def in_range(values, bounds):
    lo,hi=bounds
    result=np.ones(values.shape,dtype=bool)
    if lo is not None: result &= values>=float(lo)
    if hi is not None: result &= values<=float(hi)
    return result

def classify(args):
    src=Path(args.input).resolve()
    valpath=Path(args.validation_report).resolve()
    cfgpath=Path(args.config).resolve()
    validation=require_validation(valpath,args.body)
    cfg=load_config(cfgpath)
    window=args.window
    if window<3 or window%2==0: raise ValueError("--window must be an odd integer >= 3.")
    with rasterio.open(src) as ds:
        if ds.crs is None: raise ValueError("Raster CRS missing.")
        if not 1<=args.band<=ds.count: raise ValueError("Band index out of range.")
        if ds.transform.a==0 or ds.transform.e==0 or ds.transform.b!=0 or ds.transform.d!=0:
            raise ValueError("Rotated or degenerate grids are unsupported.")
        if not args.pixel_size_units: raise ValueError("Explicit --pixel-size-units is required.")
        if args.vertical_units not in ("m","km"): raise ValueError("Supply verified --vertical-units m or km.")
        arr=ds.read(args.band,masked=True).astype("float64")
        scale=ds.scales[args.band-1] if ds.scales else 1.0
        offset=ds.offsets[args.band-1] if ds.offsets else 0.0
        z=np.asarray(arr.filled(np.nan),dtype=float)*scale+offset
        # Convert declared vertical values to the declared horizontal spacing unit
        # only for slope; both units must be metric.
        factor=1000.0 if args.vertical_units=="km" else 1.0
        hfactor=1000.0 if args.pixel_size_units=="km" else 1.0
        if args.pixel_size_units=="degree":
            raise ValueError("Slope in geographic degrees is unsupported; explicitly project to a suitable metric grid.")
        dx=abs(ds.transform.a)*hfactor; dy=abs(ds.transform.e)*hfactor
        z=z*factor
        meta={"width":ds.width,"height":ds.height,"crs":ds.crs.to_string(),
              "bounds":[ds.bounds.left,ds.bounds.bottom,ds.bounds.right,ds.bounds.top],
              "pixelSize":[abs(ds.transform.a),abs(ds.transform.e)],
              "pixelSizeUnits":args.pixel_size_units,"verticalUnits":args.vertical_units,
              "band":args.band,"bandUnit":ds.units[args.band-1] if ds.units else None,
              "scale":scale,"offset":offset,"nodata":ds.nodata}
        profile=ds.profile.copy()
    valid=np.isfinite(z)
    if valid.sum()<window*window: raise ValueError("Insufficient valid pixels for requested neighborhood.")
    safe=np.where(valid,z,np.nan)
    gy,gx=np.gradient(safe,dy,dx)
    slope=np.degrees(np.arctan(np.hypot(gx,gy)))
    tpi,local_std,complete=neighborhood(z,valid,window)
    valid &= complete & np.isfinite(slope) & np.isfinite(tpi) & np.isfinite(local_std)
    labels=np.zeros(z.shape,dtype=np.uint16)
    class_summaries=[]
    for idx,rule in enumerate(cfg["classes"],start=1):
        mask=valid.copy()
        mask &= in_range(slope,rule["slopeDegrees"])
        mask &= in_range(tpi,rule["tpi"])
        mask &= in_range(local_std,rule["localStdDev"])
        # Earlier rules have precedence; overlaps are reported, not silently hidden.
        mask &= labels==0
        labels[mask]=idx
        class_summaries.append({"id":idx,"name":rule["name"],"pixelCount":int(mask.sum()),
                                "rule":{"slopeDegrees":rule["slopeDegrees"],"tpi":rule["tpi"],
                                        "localStdDev":rule["localStdDev"]}})
    unclassified=int((valid & (labels==0)).sum())
    counts={"validFeaturePixels":int(valid.sum()),"excludedPixels":int(labels.size-valid.sum()),
            "classifiedPixels":int((labels>0).sum()),"unclassifiedValidPixels":unclassified}
    report={
      "schemaVersion":"1.0","classifier":"TERRASCAN Stage 24 deterministic rule engine",
      "generatedAt":datetime.now(timezone.utc).isoformat(),"body":args.body,
      "source":str(src),"sourceSha256":sha256(src),"sourceMetadata":meta,
      "validationReport":str(valpath),"validationReportSha256":sha256(valpath),
      "validationOverall":(validation.get("summary") or {}).get("overall"),
      "configuration":str(cfgpath),"configurationSha256":sha256(cfgpath),
      "configurationName":cfg.get("name","user-defined rules"),"neighborhoodWindowPixels":window,
      "counts":counts,"classes":class_summaries,
      "classIdZeroMeaning":"No-data, incomplete neighborhood, or no rule matched.",
      "overlapPolicy":"First matching class in configuration order wins; reorder rules only after scientific review.",
      "scientificDisposition":"exploratory-rule-output-pending-human-review",
      "evidenceApproval":"unchanged","similarityScores":"not-computed",
      "limitations":[
        "This is not machine learning, a trained classifier, or a validated geological/geomorphological taxonomy.",
        "All class names and thresholds are operator-supplied and must be justified by authoritative literature or mission requirements.",
        "Class order determines precedence when rule ranges overlap.",
        "Slope assumes verified metric horizontal and vertical units and a suitable local projected grid.",
        "Planetary curvature, map distortion, vertical datum, illumination, sensor artefacts and geologic context are not modelled.",
        "No Earth/Moon/Mars cross-body transfer, site ranking, mission suitability or evidence approval is performed."
      ]
    }
    raster_out=Path(args.output_raster).resolve() if args.output_raster else OUT/f"{src.stem}-{args.body.lower()}-classes.tif"
    report_out=Path(args.output_report).resolve() if args.output_report else OUT/f"{src.stem}-{args.body.lower()}-classification.json"
    if raster_out.exists() or report_out.exists(): raise FileExistsError("Output exists; refusing to overwrite classification artefacts.")
    raster_out.parent.mkdir(parents=True,exist_ok=True)
    profile.update(driver="GTiff",count=1,dtype="uint16",nodata=0,compress="deflate")
    with rasterio.open(raster_out,"w",**profile) as dst:
        dst.write(labels,1)
        dst.set_band_description(1,"user-configured surface feature class ID")
        dst.update_tags(1,CLASS_CONFIG_SHA256=sha256(cfgpath),CLASSIFIER="TERRASCAN Stage 24",ZERO_VALUE="unclassified-or-no-data")
    report["classificationRaster"]=str(raster_out)
    report["classificationRasterSha256"]=sha256(raster_out)
    immutable_json(report_out,report)
    return {"classificationRaster":str(raster_out),"report":str(report_out),
            "rasterSha256":report["classificationRasterSha256"],"counts":counts,
            "scientificDisposition":report["scientificDisposition"]}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input"); ap.add_argument("--validation-report",required=True)
    ap.add_argument("--config",required=True); ap.add_argument("--body",required=True,choices=["Earth","Moon","Mars"])
    ap.add_argument("--band",type=int,default=1); ap.add_argument("--window",type=int,default=3)
    ap.add_argument("--pixel-size-units",required=True,choices=["m","km"])
    ap.add_argument("--vertical-units",required=True,choices=["m","km"])
    ap.add_argument("--output-raster"); ap.add_argument("--output-report")
    args=ap.parse_args()
    try: print(json.dumps(classify(args),indent=2))
    except Exception as exc: print(f"ERROR: {type(exc).__name__}: {exc}",file=sys.stderr); raise SystemExit(1)
if __name__=="__main__": main()
