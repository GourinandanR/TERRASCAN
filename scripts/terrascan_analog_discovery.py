#!/usr/bin/env python3
"""TERRASCAN Stage 25: explainable, evidence-gated planetary analog discovery.

This is a transparent nearest-neighbour ranking method over supplied approved
features, not a trained AI model. No candidate or target measurements are bundled.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"analog-discovery"
HASH_RE=re.compile(r"^[0-9a-f]{64}$")

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def validate_feature(feature, where):
    if not isinstance(feature,dict): raise ValueError(f"{where} must be an object.")
    for key in ("value","unit","status","manifestStatus","sourceSha256"):
        if key not in feature: raise ValueError(f"{where} missing {key}.")
    value=feature["value"]
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(float(value)):
        raise ValueError(f"{where}.value must be a finite number.")
    if not isinstance(feature["unit"],str) or not feature["unit"].strip():
        raise ValueError(f"{where}.unit must be explicit.")
    if feature["status"]!="approved" or feature["manifestStatus"]!="approved":
        return "not-approved"
    if not isinstance(feature["sourceSha256"],str) or not HASH_RE.fullmatch(feature["sourceSha256"]):
        return "invalid-provenance"
    return "approved"

def run(payload, payload_path):
    target=payload.get("target") or {}
    body=str(target.get("body","")).lower()
    if body not in ("moon","mars"):
        raise ValueError("Target body must be Moon or Mars; Earth-to-Earth analog ranking is outside this workflow.")
    target_features=target.get("features")
    definitions=payload.get("featureDefinitions")
    candidates=payload.get("candidates")
    if not isinstance(target_features,dict) or not target_features:
        raise ValueError("target.features must contain reviewed numeric feature records.")
    if not isinstance(definitions,list) or not definitions:
        raise ValueError("featureDefinitions must be a non-empty list.")
    if not isinstance(candidates,list):
        raise ValueError("candidates must be an array, even when empty.")
    seen=set(); defs=[]
    for d in definitions:
        name=d.get("name") if isinstance(d,dict) else None
        if not isinstance(name,str) or not name.strip() or name in seen:
            raise ValueError("Feature definition names must be unique non-empty strings.")
        seen.add(name)
        w=float(d.get("weight",0)); tol=float(d.get("tolerance",0))
        if not math.isfinite(w) or w<=0 or not math.isfinite(tol) or tol<=0:
            raise ValueError(f"{name}: weight and tolerance must be positive finite numbers.")
        if not isinstance(d.get("unit"),str) or not d["unit"].strip():
            raise ValueError(f"{name}: explicit unit required.")
        defs.append({"name":name,"weight":w,"tolerance":tol,"unit":d["unit"]})
    total_weight=sum(d["weight"] for d in defs)
    target_states={}
    for d in defs:
        f=target_features.get(d["name"])
        if f is None:
            target_states[d["name"]]="missing-target-feature"; continue
        state=validate_feature(f,f"target.features.{d['name']}")
        if state!="approved": target_states[d["name"]]=state; continue
        if f["unit"]!=d["unit"]: target_states[d["name"]]="unit-mismatch"; continue
        target_states[d["name"]]="approved"
    target_ready=all(target_states.get(d["name"])=="approved" for d in defs)
    results=[]
    for c in candidates:
        cid=c.get("id"); name=c.get("name")
        if not isinstance(cid,str) or not cid.strip() or not isinstance(name,str) or not name.strip():
            raise ValueError("Every candidate requires non-empty id and name.")
        if str(c.get("body","")).lower()!="earth":
            results.append({"id":cid,"name":name,"status":"excluded","reason":"Candidate body must be Earth."})
            continue
        feats=c.get("features") or {}
        contributions=[]; missing=[]
        for d in defs:
            fname=d["name"]; tf=target_features.get(fname); cf=feats.get(fname)
            if target_states.get(fname)!="approved":
                missing.append({"feature":fname,"reason":"target-"+target_states.get(fname,"missing")}); continue
            if cf is None:
                missing.append({"feature":fname,"reason":"candidate-feature-missing"}); continue
            state=validate_feature(cf,f"candidate[{cid}].features.{fname}")
            if state!="approved":
                missing.append({"feature":fname,"reason":state}); continue
            if cf["unit"]!=d["unit"]:
                missing.append({"feature":fname,"reason":"unit-mismatch"}); continue
            delta=abs(float(tf["value"])-float(cf["value"]))
            normalized=min(delta/d["tolerance"],1.0)
            contribution={"feature":fname,"targetValue":float(tf["value"]),
                "candidateValue":float(cf["value"]),"unit":d["unit"],
                "absoluteDifference":delta,"tolerance":d["tolerance"],
                "normalizedDifference":normalized,"weight":d["weight"],
                "weightedSimilarityContribution":d["weight"]*(1-normalized)}
            contributions.append(contribution)
        if missing or not target_ready or len(contributions)!=len(defs):
            results.append({"id":cid,"name":name,"status":"unranked-incomplete",
                            "missingOrRejectedFeatures":missing,"featureComparisons":contributions,
                            "ranking":"withheld-until-all-required-features-approved"})
            continue
        score=100*sum(x["weightedSimilarityContribution"] for x in contributions)/total_weight
        results.append({"id":cid,"name":name,"status":"ranked","similarityScore":round(score,4),
                        "featureComparisons":contributions,
                        "interpretation":"Weighted normalized feature agreement; not a probability or mission-suitability score."})
    ranked=sorted((x for x in results if x["status"]=="ranked"),
                  key=lambda x:(-x["similarityScore"],x["id"]))
    for idx,item in enumerate(ranked,1): item["rank"]=idx
    # Reassemble with ranks retained; ranking is deterministic.
    report={"schemaVersion":"1.0","engine":"TERRASCAN Stage 25 explainable weighted nearest-neighbour",
        "generatedAt":datetime.now(timezone.utc).isoformat(),"target":{"body":target.get("body"),"id":target.get("id")},
        "input":str(Path(payload_path).resolve()),"inputSha256":sha256(payload_path),
        "featureDefinitions":defs,"targetFeatureStates":target_states,
        "targetReady":target_ready,"candidateCount":len(candidates),
        "rankedCount":len(ranked),"unrankedCount":sum(x["status"]!="ranked" for x in results),
        "results":ranked+[x for x in results if x["status"]!="ranked"],
        "scoringMethod":{"formula":"100 * sum(weight_i * (1 - min(abs(target_i-candidate_i)/tolerance_i, 1))) / sum(weight_i)",
            "weights":"Normalized by total configured weight.",
            "tolerance":"User-supplied feature-specific absolute difference at which contribution reaches zero.",
            "ranking":"Descending score; candidate ID breaks ties."},
        "scientificDisposition":"exploratory-ranking-pending-human-review",
        "evidenceApproval":"unchanged","missionSuitability":"not-assessed",
        "limitations":["This is not a trained AI/ML model; it is a deterministic weighted nearest-neighbour method.",
            "Feature definitions, units, weights and tolerances require scientific justification and review.",
            "Only features with approved observation and source manifest states plus a valid SHA-256 field are eligible.",
            "A SHA-256 string is checked for format, not independently verified against a file in this operation.",
            "The score is feature agreement under the supplied tolerances, not probability, geological equivalence or mission suitability.",
            "Unmodelled features, spatial context, uncertainty, scale, temporal variation and data representativeness can materially affect interpretation.",
            "No Earth analog measurements, target values, rankings or mission decisions are fabricated."]}
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",help="JSON file containing target, featureDefinitions and Earth candidates")
    ap.add_argument("--output",help="Output JSON path; existing files are never overwritten")
    a=ap.parse_args()
    try:
        p=Path(a.input).resolve(); report=run(load_json(p),p)
        out=Path(a.output).resolve() if a.output else OUT/f"{p.stem}-analog-discovery.json"
        out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists(): raise FileExistsError(f"Refusing to overwrite {out}")
        out.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
        print(json.dumps({"report":str(out),"sha256":sha256(out),"ranked":report["rankedCount"],
                          "unranked":report["unrankedCount"],"targetReady":report["targetReady"]},indent=2))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}",file=sys.stderr); raise SystemExit(1)
if __name__=="__main__": main()
