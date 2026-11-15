#!/usr/bin/env python3
"""Group-aware, uncertainty-reporting supervised terrain regression.

Requires operator-supplied labelled observations. Predictions are exploratory
and never approve evidence, rank sites, or authorize mission operations.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA="terrascan.predictive-training.v1"
SHA_RE=re.compile(r"^[0-9a-f]{64}$")

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def load_data(path:Path):
    d=json.loads(path.read_text(encoding="utf-8"))
    if d.get("schema_version")!=SCHEMA: raise ValueError(f"schema_version must be {SCHEMA}")
    names=d.get("feature_names")
    if not isinstance(names,list) or not names or len(set(names))!=len(names) or not all(isinstance(n,str) and n.strip() for n in names):
        raise ValueError("feature_names must be a non-empty ordered list of unique names")
    target=d.get("target")
    if not isinstance(target,dict) or not isinstance(target.get("name"),str) or not target["name"].strip() or not isinstance(target.get("unit"),str) or not target["unit"].strip():
        raise ValueError("target.name and target.unit are required")
    samples=d.get("samples")
    if not isinstance(samples,list) or len(samples)<12: raise ValueError("At least 12 labelled samples are required")
    X=[]; y=[]; groups=[]; ids=[]; seen=set()
    for i,s in enumerate(samples):
        sid=s.get("sample_id")
        if not isinstance(sid,str) or not sid or sid in seen: raise ValueError(f"sample {i}: sample_id must be unique and non-empty")
        seen.add(sid)
        group=s.get("spatial_group_id")
        if not isinstance(group,str) or not group.strip(): raise ValueError(f"sample {sid}: spatial_group_id is required for group-aware splitting")
        v=s.get("target_value")
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError(f"sample {sid}: target_value must be finite numeric")
        fs=s.get("features")
        if not isinstance(fs,dict) or set(fs)!=set(names): raise ValueError(f"sample {sid}: feature keys must exactly match feature_names")
        row=[]
        for n in names:
            x=fs[n]
            if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x): raise ValueError(f"sample {sid}: feature {n} must be finite numeric")
            row.append(float(x))
        src=s.get("source")
        if not isinstance(src,dict) or not isinstance(src.get("source_id"),str) or not src["source_id"] or not SHA_RE.fullmatch(str(src.get("sha256",""))):
            raise ValueError(f"sample {sid}: source_id and lowercase SHA-256 are required")
        if not isinstance(s.get("target_basis"),str) or not s["target_basis"].strip(): raise ValueError(f"sample {sid}: target_basis is required")
        X.append(row); y.append(float(v)); groups.append(group); ids.append(sid)
    if len(set(groups))<6: raise ValueError("At least six distinct spatial_group_id values are required for train/calibration/test separation")
    return d,names,X,y,groups,ids

def fit(dataset:Path,outdir:Path,seed:int=42,trees:int=400,coverage:float=.90):
    if not .5<=coverage<=.99: raise ValueError("coverage must be between 0.50 and 0.99")
    if not 20<=trees<=5000: raise ValueError("trees must be between 20 and 5000")
    d,names,X,y,groups,ids=load_data(dataset)
    try:
        import joblib, sklearn
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import GroupShuffleSplit
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    except ImportError as e: raise RuntimeError("Install optional dependencies: pip install -r requirements-ml.txt") from e
    idx=list(range(len(y)))
    first=GroupShuffleSplit(n_splits=1,test_size=.20,random_state=seed)
    traincal_idx,test_idx=next(first.split(idx,y,groups))
    traincal_groups=[groups[i] for i in traincal_idx]
    second=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=seed+1)
    tr_rel,cal_rel=next(second.split(traincal_idx,[y[i] for i in traincal_idx],traincal_groups))
    train_idx=[traincal_idx[i] for i in tr_rel]; cal_idx=[traincal_idx[i] for i in cal_rel]
    train_groups={groups[i] for i in train_idx}; cal_groups={groups[i] for i in cal_idx}; test_groups={groups[i] for i in test_idx}
    if train_groups&cal_groups or train_groups&test_groups or cal_groups&test_groups: raise RuntimeError("Spatial group leakage detected")
    if len(train_idx)<4 or len(cal_idx)<2 or len(test_idx)<2: raise ValueError("Split produced too few samples; supply more independent spatial groups")
    model=RandomForestRegressor(n_estimators=trees,random_state=seed,n_jobs=1,min_samples_leaf=2)
    model.fit([X[i] for i in train_idx],[y[i] for i in train_idx])
    cal_pred=model.predict([X[i] for i in cal_idx])
    abs_res=np.abs(np.asarray([y[i] for i in cal_idx])-cal_pred)
    # Finite-sample higher empirical quantile; interval is approximate, not a guarantee.
    rank=min(len(abs_res),max(1,math.ceil((len(abs_res)+1)*coverage)))
    radius=float(np.sort(abs_res)[rank-1])
    test_pred=model.predict([X[i] for i in test_idx])
    actual=np.asarray([y[i] for i in test_idx]); residual=actual-test_pred
    lower=test_pred-radius; upper=test_pred+radius
    outdir.mkdir(parents=True,exist_ok=False)
    model_path=outdir/"regressor.joblib"
    joblib.dump({"model":model,"feature_names":names,"target":d["target"],"schema_version":SCHEMA,
                 "training_dataset_sha256":digest(dataset),"random_seed":seed,"interval_radius":radius,"nominal_coverage":coverage},model_path)
    report={
      "schema_version":"terrascan.predictive-evaluation.v1","created_utc":datetime.now(timezone.utc).isoformat(),
      "status":"trained-evaluated","model_type":"RandomForestRegressor","sklearn_version":sklearn.__version__,
      "training_dataset_sha256":digest(dataset),"model_sha256":digest(model_path),
      "target":d["target"],"feature_names":names,"sample_count":len(y),
      "split":{"method":"two-stage GroupShuffleSplit","seed":seed,"train_samples":len(train_idx),"calibration_samples":len(cal_idx),"test_samples":len(test_idx),
               "train_groups":len(train_groups),"calibration_groups":len(cal_groups),"test_groups":len(test_groups),"group_overlap":False},
      "metrics":{"mae":float(mean_absolute_error(actual,test_pred)),"rmse":float(math.sqrt(mean_squared_error(actual,test_pred))),
                 "r2":float(r2_score(actual,test_pred)) if len(actual)>1 else None},
      "interval":{"method":"symmetric absolute-residual calibration quantile","nominal_coverage":coverage,
                  "calibration_sample_count":len(cal_idx),"absolute_residual_radius":radius,
                  "test_empirical_coverage":float(np.mean((actual>=lower)&(actual<=upper))),
                  "test_mean_interval_width":float(np.mean(upper-lower)),
                  "warning":"Small calibration sets yield coarse intervals. Empirical coverage is not a guarantee and may fail under distribution shift."},
      "test_residual_summary":{"mean":float(np.mean(residual)),"median_absolute":float(np.median(np.abs(residual))),
                               "p95_absolute":float(np.quantile(np.abs(residual),.95))},
      "review_status":"pending-human-review","evidence_approval":"unchanged","mission_authorization":"not-assessed",
      "generalization_warning":"Performance applies only to this supplied dataset and group split; it does not establish cross-body, cross-sensor or future-condition predictive validity."
    }
    (outdir/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def predict(model_path:Path,input_path:Path,output_path:Path):
    try: import joblib
    except ImportError as e: raise RuntimeError("Install optional dependencies: pip install -r requirements-ml.txt") from e
    b=joblib.load(model_path); d=json.loads(input_path.read_text(encoding="utf-8"))
    names=b["feature_names"]
    if d.get("feature_names")!=names: raise ValueError("Inference feature_names must exactly match model names and order")
    samples=d.get("samples")
    if not isinstance(samples,list) or not samples: raise ValueError("No inference samples supplied")
    rows=[]
    for s in samples:
        fs=s.get("features",{})
        if set(fs)!=set(names): raise ValueError(f"sample {s.get('sample_id')}: feature schema mismatch")
        row=[fs[n] for n in names]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in row): raise ValueError("All inference features must be finite numeric values")
        rows.append(row)
    pred=b["model"].predict(rows); radius=float(b["interval_radius"])
    result={"schema_version":"terrascan.predictive-results.v1","model_sha256":digest(model_path),
      "status":"exploratory-pending-human-review","target":b["target"],"interval_nominal_coverage":b["nominal_coverage"],
      "results":[{"sample_id":s.get("sample_id"),"predicted_value":float(v),"lower_bound":float(v-radius),"upper_bound":float(v+radius),
                  "interval_note":"Approximate residual-calibrated interval; not a guaranteed coverage bound.",
                  "review_status":"pending-human-review"} for s,v in zip(samples,pred)],
      "limitations":["No prediction is valid outside the feature and target definitions represented by reviewed training data.",
        "Intervals may be unreliable under spatial, sensor, planetary-body or environmental distribution shift.",
        "Predictions do not approve evidence, rank sites, assess mission suitability or authorize operations."]}
    output_path.parent.mkdir(parents=True,exist_ok=True); output_path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="cmd",required=True)
    t=sub.add_parser("train"); t.add_argument("dataset",type=Path); t.add_argument("--output-dir",type=Path,required=True); t.add_argument("--seed",type=int,default=42); t.add_argument("--trees",type=int,default=400); t.add_argument("--coverage",type=float,default=.90)
    q=sub.add_parser("predict"); q.add_argument("model",type=Path); q.add_argument("input",type=Path); q.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        r=fit(a.dataset,a.output_dir,a.seed,a.trees,a.coverage) if a.cmd=="train" else predict(a.model,a.input,a.output)
        print(json.dumps({"status":r["status"],"report":str(a.output_dir/"evaluation.json") if a.cmd=="train" else str(a.output)},indent=2))
    except Exception as e: print(f"TERRASCAN predictive error: {e}",file=sys.stderr); return 2
    return 0
if __name__=="__main__": raise SystemExit(main())
