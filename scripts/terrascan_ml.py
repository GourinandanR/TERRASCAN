#!/usr/bin/env python3
"""Evidence-aware supervised terrain pattern recognition.

This optional scikit-learn workflow trains only on operator-supplied labelled samples.
It never creates training examples, approves evidence, or makes mission decisions.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "terrascan.ml-training.v1"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_dataset(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA:
        raise ValueError(f"schema_version must be {SCHEMA}")
    names = data.get("feature_names")
    if not isinstance(names, list) or not names or len(set(names)) != len(names):
        raise ValueError("feature_names must be a non-empty list of unique names")
    if not all(isinstance(n, str) and n.strip() for n in names):
        raise ValueError("feature names must be non-empty strings")
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("No labelled samples supplied; model status remains not-trained")
    rows, labels, ids = [], [], []
    seen = set()
    for i, sample in enumerate(samples):
        sid = sample.get("sample_id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError(f"sample {i}: sample_id must be unique and non-empty")
        seen.add(sid)
        label = sample.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"sample {sid}: explicit non-empty label required")
        features = sample.get("features")
        if not isinstance(features, dict) or set(features) != set(names):
            raise ValueError(f"sample {sid}: feature keys must exactly match feature_names")
        vals=[]
        for name in names:
            value=features[name]
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
                raise ValueError(f"sample {sid}: feature {name} must be finite numeric")
            vals.append(float(value))
        source = sample.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str) or not source["source_id"]:
            raise ValueError(f"sample {sid}: source.source_id is required")
        if not SHA_RE.fullmatch(str(source.get("sha256",""))):
            raise ValueError(f"sample {sid}: source.sha256 must be a 64-character lowercase SHA-256")
        if not isinstance(sample.get("label_basis"), str) or not sample["label_basis"].strip():
            raise ValueError(f"sample {sid}: label_basis is required")
        rows.append(vals); labels.append(label); ids.append(sid)
    classes = sorted(set(labels))
    counts={c:labels.count(c) for c in classes}
    if len(classes) < 2:
        raise ValueError("At least two distinct labelled classes are required")
    if min(counts.values()) < 2:
        raise ValueError("Each class requires at least two samples for stratified evaluation")
    return data, names, rows, labels, ids, counts

def train(dataset_path: Path, output_dir: Path, test_fraction: float=0.25, seed: int=42, trees: int=300):
    if not 0.1 <= test_fraction <= 0.5:
        raise ValueError("test_fraction must be between 0.1 and 0.5")
    if trees < 10 or trees > 5000:
        raise ValueError("trees must be between 10 and 5000")
    data,names,X,y,ids,counts=load_dataset(dataset_path)
    # Import lazily so the base TERRASCAN application does not require ML packages.
    try:
        import joblib
        import sklearn
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
    except ImportError as exc:
        raise RuntimeError("Install optional dependencies: pip install -r requirements-ml.txt") from exc
    indices=list(range(len(y)))
    train_idx,test_idx=train_test_split(indices,test_size=test_fraction,random_state=seed,stratify=y)
    model=RandomForestClassifier(n_estimators=trees,random_state=seed,class_weight="balanced",n_jobs=1)
    model.fit([X[i] for i in train_idx],[y[i] for i in train_idx])
    pred=model.predict([X[i] for i in test_idx])
    labels=sorted(set(y))
    report=classification_report([y[i] for i in test_idx],pred,labels=labels,output_dict=True,zero_division=0)
    output_dir.mkdir(parents=True,exist_ok=False)
    bundle={"model":model,"feature_names":names,"classes":labels,"schema_version":SCHEMA,
            "training_dataset_sha256":sha256(dataset_path),"random_seed":seed}
    model_path=output_dir/"model.joblib"
    joblib.dump(bundle,model_path)
    metrics={
      "schema_version":"terrascan.ml-evaluation.v1","created_utc":datetime.now(timezone.utc).isoformat(),
      "status":"trained-evaluated","model_type":"RandomForestClassifier",
      "scikit_learn_version":sklearn.__version__,"training_dataset_sha256":sha256(dataset_path),
      "model_sha256":sha256(model_path),"sample_count":len(y),"class_counts":counts,
      "train_count":len(train_idx),"test_count":len(test_idx),"feature_names":names,
      "classes":labels,"random_seed":seed,"test_fraction":test_fraction,"n_estimators":trees,
      "accuracy":float(accuracy_score([y[i] for i in test_idx],pred)),
      "confusion_matrix":{"labels":labels,"values":confusion_matrix([y[i] for i in test_idx],pred,labels=labels).tolist()},
      "class_metrics":report,
      "evaluation_note":"Metrics describe only this supplied sample split; they are not evidence of planetary generalisation or mission performance.",
      "review_status":"pending-human-review","evidence_approval":"unchanged","mission_authorization":"not-assessed"
    }
    (output_dir/"evaluation.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    return metrics

def predict(model_path: Path, input_path: Path, output_path: Path):
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("Install optional dependencies: pip install -r requirements-ml.txt") from exc
    bundle=joblib.load(model_path)
    data=json.loads(input_path.read_text(encoding="utf-8"))
    names=bundle.get("feature_names")
    if data.get("feature_names") != names:
        raise ValueError("Inference feature_names must exactly match the model schema and order")
    samples=data.get("samples")
    if not isinstance(samples,list) or not samples:
        raise ValueError("No inference samples supplied")
    X=[]
    for s in samples:
        features=s.get("features",{})
        if set(features)!=set(names):
            raise ValueError(f"sample {s.get('sample_id')}: feature keys mismatch")
        row=[features[n] for n in names]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in row):
            raise ValueError(f"sample {s.get('sample_id')}: features must be finite numeric")
        X.append(row)
    preds=bundle["model"].predict(X)
    probs=bundle["model"].predict_proba(X)
    out={"schema_version":"terrascan.ml-predictions.v1","model_sha256":sha256(model_path),
         "status":"exploratory-pending-human-review","results":[
           {"sample_id":s.get("sample_id"),"predicted_class":str(pred),
            "class_probabilities":{str(c):float(p) for c,p in zip(bundle["classes"],prob)},
            "review_status":"pending-human-review"} for s,pred,prob in zip(samples,preds,probs)],
         "limitations":["Classifier confidence values are not calibrated probabilities unless separately calibrated and validated.",
                        "Training/test performance does not establish transfer to a different planetary body, sensor, resolution or processing chain.",
                        "Predictions do not approve evidence, rank sites or assess mission suitability."]}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    t=sub.add_parser("train"); t.add_argument("dataset",type=Path); t.add_argument("--output-dir",type=Path,required=True)
    t.add_argument("--test-fraction",type=float,default=.25); t.add_argument("--seed",type=int,default=42); t.add_argument("--trees",type=int,default=300)
    q=sub.add_parser("predict"); q.add_argument("model",type=Path); q.add_argument("input",type=Path); q.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.command=="train":
            r=train(a.dataset,a.output_dir,a.test_fraction,a.seed,a.trees); print(json.dumps({"status":r["status"],"model_sha256":r["model_sha256"],"evaluation":str(a.output_dir/"evaluation.json")},indent=2))
        else:
            r=predict(a.model,a.input,a.output); print(json.dumps({"status":r["status"],"output":str(a.output)},indent=2))
    except Exception as exc:
        print(f"TERRASCAN ML error: {exc}",file=sys.stderr); return 2
    return 0
if __name__=="__main__": raise SystemExit(main())
