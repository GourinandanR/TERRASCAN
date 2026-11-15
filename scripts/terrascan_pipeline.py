#!/usr/bin/env python3
"""Stage 13 batch orchestration for controlled planetary dataset ingestion.

The pipeline never approves evidence, invents measurements, or downloads unless
explicitly requested through the existing allow-listed downloader.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / 'scripts' / 'terrascan_ingest.py'
MANIFEST_DIR = ROOT / 'data' / 'manifests'
RUN_DIR = ROOT / 'data' / 'pipeline-runs'
ALLOWED = {'moon-lola-dem','mars-mola-megdr','mars-themis-global-ir','mars-tes-thermal-inertia','mars-global-geology'}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def safe_project_file(value: str) -> Path:
    p=(ROOT / value).resolve()
    if p != ROOT and ROOT not in p.parents:
        raise ValueError(f'Path escapes project root: {value}')
    if not p.is_file(): raise FileNotFoundError(f'Input file not found: {value}')
    return p

def run_cmd(args: list[str]) -> dict[str,Any]:
    proc=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    return {'command':args,'returncode':proc.returncode,'stdout':proc.stdout.strip(),'stderr':proc.stderr.strip()}

def api_post(base: str, path: str, payload: dict) -> dict:
    req=urllib.request.Request(base.rstrip('/')+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=15) as res: return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors='replace')
        if e.code==409: return {'status':'already-registered','detail':body}
        raise RuntimeError(f'API returned HTTP {e.code}: {body}') from e

def process_job(job: dict, sync_api: str|None=None) -> dict:
    required={'dataset_id','file','source_url','provider'}
    missing=required-set(job)
    if missing: raise ValueError('Missing job fields: '+', '.join(sorted(missing)))
    if job['dataset_id'] not in ALLOWED: raise ValueError('Unknown dataset_id; use a dataset in the controlled catalogue')
    source=safe_project_file(job['file'])
    digest=sha256(source)
    expected=job.get('expected_sha256')
    if expected and digest.lower()!=str(expected).lower(): raise ValueError('Input SHA-256 does not match expected_sha256')
    existing=list(MANIFEST_DIR.glob(f"{job['dataset_id']}-{digest[:12]}.json"))
    if existing:
        manifest=json.loads(existing[0].read_text(encoding='utf-8'))
        if manifest.get('checksumSha256') != digest: raise ValueError('Manifest filename collision or checksum mismatch')
        outcome={'status':'manifest-already-exists','manifest':str(existing[0].relative_to(ROOT)),'sha256':digest}
    else:
        inspect=run_cmd([sys.executable,str(INGEST),'inspect',str(source),'--dataset-id',job['dataset_id']])
        if inspect['returncode'] != 0: raise RuntimeError(inspect['stderr'] or inspect['stdout'])
        report=json.loads(inspect['stdout'])
        manifest_cmd=[sys.executable,str(INGEST),'manifest',str(ROOT/report['report']),'--dataset-id',job['dataset_id'],'--source-url',job['source_url'],'--provider',job['provider']]
        if job.get('source_title'): manifest_cmd += ['--source-title',job['source_title']]
        if job.get('product_version'): manifest_cmd += ['--product-version',job['product_version']]
        if job.get('retrieved_at'): manifest_cmd += ['--retrieved-at',job['retrieved_at']]
        made=run_cmd(manifest_cmd)
        if made['returncode'] != 0: raise RuntimeError(made['stderr'] or made['stdout'])
        result=json.loads(made['stdout']); mpath=ROOT/result['manifest']
        manifest=json.loads(mpath.read_text(encoding='utf-8'))
        outcome={'status':'manifest-created-pending-review','manifest':result['manifest'],'sha256':digest,'inspection':report['report']}
    if sync_api:
        payload={'dataset_id':manifest['datasetId'],'version':manifest.get('productVersion','not-recorded'),'sha256':digest,'source_uri':manifest['sourceUrl'],'review_status':'pending-human-review','metadata':manifest}
        outcome['api']=api_post(sync_api,'/api/manifests',payload)
    return outcome

def main():
    p=argparse.ArgumentParser(description='TERRASCAN batch ingestion and provenance pipeline')
    p.add_argument('config',help='JSON pipeline job file')
    p.add_argument('--sync-api',help='Optional API base URL; only pending-review provenance manifests are submitted')
    p.add_argument('--stop-on-error',action='store_true')
    a=p.parse_args()
    config_path=safe_project_file(a.config)
    config=json.loads(config_path.read_text(encoding='utf-8'))
    jobs=config.get('jobs')
    if not isinstance(jobs,list): raise ValueError('Config must contain a jobs array')
    started=datetime.now(timezone.utc).isoformat(); results=[]
    for index,job in enumerate(jobs):
        try: results.append({'index':index,'dataset_id':job.get('dataset_id'),'ok':True,**process_job(job,a.sync_api)})
        except Exception as e:
            results.append({'index':index,'dataset_id':job.get('dataset_id') if isinstance(job,dict) else None,'ok':False,'error':f'{type(e).__name__}: {e}'})
            if a.stop_on_error: break
    report={'schemaVersion':'1.0','pipeline':'terrascan-stage13','startedAt':started,'finishedAt':datetime.now(timezone.utc).isoformat(),'jobCount':len(jobs),'succeeded':sum(bool(x['ok']) for x in results),'failed':sum(not x['ok'] for x in results),'results':results,'policy':['No scientific measurements are fabricated.','All generated manifests remain pending human review.','No network access occurs unless --sync-api is supplied; this pipeline does not download files.']}
    RUN_DIR.mkdir(parents=True,exist_ok=True)
    out=RUN_DIR/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-pipeline-report.json')
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(out.relative_to(ROOT)),**{k:report[k] for k in ('jobCount','succeeded','failed')}},indent=2))
    if report['failed']: sys.exit(2)
if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}',file=sys.stderr); sys.exit(1)
