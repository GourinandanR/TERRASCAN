#!/usr/bin/env python3
"""TERRASCAN Stage 29 integrated project and evidence-chain quality audit."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_FILES=[
 "scripts/terrascan_ingest.py","scripts/terrascan_validate.py","scripts/terrascan_spatial.py",
 "scripts/terrascan_classify.py","scripts/terrascan_analog_discovery.py","scripts/terrascan_ml.py",
 "scripts/terrascan_predict.py","scripts/terrascan_rank_sites.py",
 "backend/app/main.py","backend/app/reporting.py","backend/app/risks.py","backend/app/scenarios.py",
 "src/components/DatasetWorkspace.tsx",
 "docs/backend/STAGE25_ANALOG_DISCOVERY.md","docs/backend/STAGE26_ML_TERRAIN_PATTERN_RECOGNITION.md",
 "docs/backend/STAGE27_PREDICTIVE_TERRAIN_ANALYSIS.md","docs/backend/STAGE28_INTELLIGENT_MISSION_SITE_RANKING.md"
]
REQUIRED_TESTS=[
 "scripts/test_terrascan_analog_discovery.py","scripts/test_terrascan_ml.py",
 "scripts/test_terrascan_predict.py","scripts/test_terrascan_rank_sites.py",
 "scripts/test_terrascan_classify.py","scripts/test_terrascan_spatial.py",
 "scripts/test_terrascan_validate.py","scripts/test_terrascan_pipeline.py",
 "backend/tests/test_api.py"
]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
def check_project(root:Path):
 checks=[]
 def add(name,ok,detail): checks.append({"check":name,"status":"pass" if ok else "fail","detail":detail})
 for rel in REQUIRED_FILES:
  p=root/rel; add("required-file:"+rel,p.is_file(),"present" if p.is_file() else "missing")
 pkg=json.loads((root/"package.json").read_text(encoding="utf-8"))
 add("package-version",pkg.get("version")=="3.8.0",f"expected 3.8.0, found {pkg.get('version')}")
 expected={"sites:rank","sites:test","predict:train","predict:run","predict:test","ml:train","ml:predict","ml:test"}
 actual=set(pkg.get("scripts",{}))
 add("npm-script-registration",expected.issubset(actual),f"missing: {sorted(expected-actual)}")
 ts=(root/"src/components/DatasetWorkspace.tsx").read_text(encoding="utf-8")
 for stage in (25,26,27,28):
  present=f"STAGE {stage}" in ts
  add(f"dataset-workspace-stage-{stage}",present,"section present" if present else "section missing")
 main=(root/"backend/app/main.py").read_text(encoding="utf-8")
 for route in ("/api/mission-profiles","/api/suitability-assessments","/api/reports/"):
  present=route in main
  add("backend-route:"+route,present,"route declaration present" if present else "route missing")
 # Compile source without writing bytecode.
 syntax_errors=[]
 for p in root.rglob("*.py"):
  if any(x in {".venv","venv","__pycache__",".pytest_cache"} for x in p.parts): continue
  try: compile(p.read_text(encoding="utf-8"),str(p),"exec")
  except Exception as e: syntax_errors.append(f"{p.relative_to(root)}: {e}")
 add("python-source-syntax",not syntax_errors,syntax_errors[:10] if syntax_errors else "all Python sources compile")
 missing_tests=[x for x in REQUIRED_TESTS if not (root/x).is_file()]
 add("regression-test-presence",not missing_tests,f"missing: {missing_tests}" if missing_tests else f"{len(REQUIRED_TESTS)} test files present")
 # Verify documented non-authorizing safeguards are explicitly present in ranking implementation.
 ranking=(root/"scripts/terrascan_rank_sites.py").read_text(encoding="utf-8")
 for token in ("mission-constraints-not-eligible","pending-human-review","missionAuthorization","uncertaintyFraction"):
  add("ranking-safeguard:"+token,token in ranking,"present" if token in ranking else "missing")
 return {"schema_version":"terrascan.integrated-qa.v1","generated_utc":datetime.now(timezone.utc).isoformat(),
  "project_root":str(root.resolve()),"project_version":pkg.get("version"),
  "check_count":len(checks),"passed":sum(c["status"]=="pass" for c in checks),
  "failed":sum(c["status"]=="fail" for c in checks),"status":"pass" if all(c["status"]=="pass" for c in checks) else "fail",
  "checks":checks,"limitations":["This is a structural and static QA audit, not a scientific validation or security certification.",
  "It does not verify external source data, scientific assumptions, model generalization, UI behavior or operational readiness."]}
def verify_artifact_manifest(path:Path):
 data=json.loads(path.read_text(encoding="utf-8"))
 items=data.get("artifacts")
 if not isinstance(items,list) or not items: raise ValueError("manifest.artifacts must be a non-empty array")
 results=[]
 for item in items:
  rel=item.get("path"); expected=item.get("sha256")
  if not isinstance(rel,str) or not isinstance(expected,str): raise ValueError("each artifact needs path and sha256")
  p=Path(rel)
  if not p.is_absolute(): p=(path.parent/p).resolve()
  if not p.is_file(): results.append({"path":str(p),"status":"missing"}); continue
  actual=sha(p)
  results.append({"path":str(p),"expected_sha256":expected,"actual_sha256":actual,
                  "status":"verified" if actual==expected else "hash-mismatch"})
 return {"schema_version":"terrascan.artifact-integrity.v1","manifest":str(path.resolve()),
         "results":results,"verified":sum(x["status"]=="verified" for x in results),
         "failed":sum(x["status"]!="verified" for x in results),
         "status":"pass" if all(x["status"]=="verified" for x in results) else "fail"}
def main():
 p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="cmd",required=True)
 a=sub.add_parser("project"); a.add_argument("--root",type=Path,default=ROOT); a.add_argument("--output",type=Path)
 b=sub.add_parser("integrity"); b.add_argument("manifest",type=Path); b.add_argument("--output",type=Path)
 args=p.parse_args()
 try:
  report=check_project(args.root.resolve()) if args.cmd=="project" else verify_artifact_manifest(args.manifest.resolve())
  if args.output:
   out=args.output.resolve()
   if out.exists(): raise ValueError(f"Refusing to overwrite existing output: {out}")
   out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
  print(json.dumps({k:report[k] for k in report if k not in ("checks","results")},indent=2))
  if report["status"]!="pass": return 1
 except Exception as e:
  print(f"TERRASCAN QA error: {e}",file=sys.stderr); return 2
 return 0
if __name__=="__main__": raise SystemExit(main())
