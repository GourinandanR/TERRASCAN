#!/usr/bin/env python3
"""TERRASCAN Stage 8 controlled planetary data ingestion (Python stdlib + optional Rasterio)."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, tempfile, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, INSPECTION, MANIFESTS = (ROOT / 'data' / x for x in ('raw', 'inspection', 'manifests'))
CATALOG = {
 'moon-lola-dem': ('Lunar Orbiter Laser Altimeter (LOLA) archive and derived DEMs', 'Moon', 'terrain', ['imbrium.mit.edu','pds-geosciences.wustl.edu','pds.nasa.gov']),
 'mars-mola-megdr': ('MOLA Mission Experiment Gridded Data Records (MEGDR)', 'Mars', 'terrain', ['pds-geosciences.wustl.edu','pds.nasa.gov']),
 'mars-themis-global-ir': ('THEMIS global daytime and nighttime infrared mosaics', 'Mars', 'thermal', ['mars.asu.edu','themis.asu.edu']),
 'mars-tes-thermal-inertia': ('TES thermal inertia global products', 'Mars', 'thermal', ['mars.asu.edu','themis.asu.edu']),
 'mars-global-geology': ('Mars global geology map and supporting map products', 'Mars', 'geology', ['marsoweb.nas.nasa.gov']),
}
def sha256(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def safe_name(s):
 n=re.sub(r'[^A-Za-z0-9._-]+','_',Path(s).name).strip('._')[:180]
 if not n: raise ValueError('Could not determine a safe filename')
 return n
class SameHostRedirect(urllib.request.HTTPRedirectHandler):
 def __init__(self,host): self.host=host.lower()
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  p=urllib.parse.urlparse(newurl)
  if p.scheme!='https' or (p.hostname or '').lower()!=self.host: raise ValueError('Redirect rejected: must remain HTTPS on the original allow-listed host')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
def download(a):
 title,body,criterion,hosts=CATALOG[a.dataset_id]; p=urllib.parse.urlparse(a.url); host=(p.hostname or '').lower()
 if p.scheme!='https' or host not in hosts or p.username or p.password: raise ValueError(f'URL rejected; HTTPS host must be one of: {hosts}')
 opener=urllib.request.build_opener(SameHostRedirect(host)); req=urllib.request.Request(a.url,headers={'User-Agent':'TERRASCAN-data-ingest/0.8','Accept':'*/*'})
 RAW.mkdir(parents=True,exist_ok=True); tmp=None
 try:
  with opener.open(req,timeout=a.timeout) as response:
   name=safe_name(a.filename or Path(p.path).name or 'download.bin')
   fd,tmpname=tempfile.mkstemp(prefix='.terrascan-',suffix='.part',dir=RAW); tmp=Path(tmpname); h=hashlib.sha256(); size=0
   with os.fdopen(fd,'wb') as out:
    while True:
     block=response.read(1024*1024)
     if not block: break
     size+=len(block)
     if size>a.max_bytes: raise ValueError(f'Download exceeds {a.max_bytes} byte limit')
     h.update(block); out.write(block)
    out.flush(); os.fsync(out.fileno())
   digest=h.hexdigest()
   if size==0: raise ValueError('Empty response')
   if a.expected_sha256 and digest.lower()!=a.expected_sha256.lower(): raise ValueError('SHA-256 mismatch; temporary file discarded')
   destdir=RAW/a.dataset_id/digest; destdir.mkdir(parents=True,exist_ok=True); dest=destdir/name
   if dest.exists():
    if sha256(dest)!=digest: raise ValueError('Destination exists with different content; refusing overwrite')
    tmp.unlink(); tmp=None
   else: os.replace(tmp,dest); tmp=None
   print(json.dumps({'datasetId':a.dataset_id,'file':str(dest.relative_to(ROOT)),'fileName':name,'sizeBytes':size,'sha256':digest,'sourceUrl':a.url,'downloadedAt':datetime.now(timezone.utc).isoformat(),'status':'downloaded-not-validated'},indent=2))
 finally:
  if tmp and tmp.exists(): tmp.unlink()
def raster_info(path):
 try: import rasterio
 except ImportError: return {'available':False,'message':'Install optional requirements-geo.txt for Rasterio inspection'}
 try:
  with rasterio.open(path) as ds:
   b=ds.bounds
   return {'available':True,'driver':ds.driver,'width':ds.width,'height':ds.height,'bandCount':ds.count,'dtypes':list(ds.dtypes),'crs':str(ds.crs) if ds.crs else None,'crsWkt':ds.crs.to_wkt() if ds.crs else None,'transform':list(ds.transform),'bounds':[b.left,b.bottom,b.right,b.top],'resolution':list(ds.res),'nodataValues':list(ds.nodatavals),'units':list(ds.units) if ds.units else None,'scales':list(ds.scales),'offsets':list(ds.offsets),'tags':ds.tags(),'bandTags':[ds.tags(i) for i in range(1,ds.count+1)],'footprintNote':'Bounds are expressed in the reported CRS; verify planetary reference frame and longitude convention against source label.'}
 except Exception as e: return {'available':True,'error':f'{type(e).__name__}: {e}'}
def pds4_label_info(path):
 """Extract selected PDS4 label values; retain as hints, not validated science metadata."""
 f=Path(path)
 if f.suffix.lower() not in ('.xml','.lbl'): return {'available':False,'reason':'Not an XML/PDS4 label filename'}
 if f.stat().st_size > 50*1024*1024: return {'available':False,'reason':'Label exceeds 50 MiB inspection limit'}
 try:
  from xml.etree import ElementTree as ET
  root=ET.parse(f).getroot()
  wanted={'logical_identifier','version_id','title','product_class','start_date_time','stop_date_time',
          'local_identifier','file_name','file_size','record_type','offset','unit','description',
          'minimum','maximum','scaling_factor','value_offset','missing_constant','saturated_constant'}
  values={}
  for el in root.iter():
   name=el.tag.split('}')[-1]
   if name in wanted and el.text and el.text.strip():
    values.setdefault(name,[]).append(el.text.strip())
  return {'available':True,'format':'XML/PDS4-like','extracted_values':values,
          'warning':'Label fields are extracted verbatim; validate product class, units, scaling, coordinate system and references against the product documentation.'}
 except Exception as e:
  return {'available':False,'error':f'{type(e).__name__}: {e}'}
def inspect(a):
 f=Path(a.file).resolve()
 if not f.is_file(): raise FileNotFoundError(f)
 title,body,criterion,_=CATALOG[a.dataset_id]; digest=sha256(f); rmeta=raster_info(f)
 report={'schemaVersion':'1.0','datasetId':a.dataset_id,'catalogTitle':title,'body':body,'criterion':criterion,'inspectedAt':datetime.now(timezone.utc).isoformat(),'sourceFile':str(f),'fileName':f.name,'sizeBytes':f.stat().st_size,'sha256':digest,'rasterMetadata':rmeta,'pds4Label':pds4_label_info(f),'review':{k:False for k in ['officialProductLabelChecked','crsAndBodyFixedFrameReviewed','unitsAndScaleOffsetReviewed','noDataAndQualityFlagsReviewed','spatialFootprintReviewed','temporalCoverageReviewed','uncertaintyReviewed','humanApproved']},'status':'inspection-only','warnings':['Opening a raster is not scientific validation.','Verify CRS, units, scale/offset, no-data, footprint and time coverage against the official product label.','Do not add this product to the evidence registry until all review gates pass.']}
 INSPECTION.mkdir(parents=True,exist_ok=True); out=INSPECTION/f'{a.dataset_id}-{digest[:12]}-inspection.json'; out.write_text(json.dumps(report,indent=2),encoding='utf8')
 print(json.dumps({'report':str(out.relative_to(ROOT)),'sha256':digest,'rasterioAvailable':rmeta.get('available'),'status':report['status']},indent=2))
def create_manifest(a):
 rp=Path(a.inspection).resolve(); report=json.loads(rp.read_text(encoding='utf8'))
 if report['datasetId']!=a.dataset_id: raise ValueError('Inspection dataset ID mismatch')
 f=Path(report['sourceFile'])
 if not f.is_file() or sha256(f)!=report['sha256']: raise ValueError('Source file missing or changed since inspection')
 if not a.source_url.startswith('https://'): raise ValueError('Source URL must use HTTPS')
 rm=report['rasterMetadata']; obj={'schemaVersion':'1.0','datasetId':a.dataset_id,'body':report['body'],'criterion':report['criterion'],'catalogTitle':report['catalogTitle'],'sourceUrl':a.source_url,'sourceTitle':a.source_title or report['catalogTitle'],'provider':a.provider,'retrievedAt':a.retrieved_at or report['inspectedAt'],'file':str(f),'fileName':f.name,'sizeBytes':report['sizeBytes'],'checksumSha256':report['sha256'],'fileFormat':rm.get('driver') or f.suffix.lstrip('.').upper() or 'unknown','rasterMetadata':rm,'productVersion':a.product_version or 'not recorded — inspect official label','coordinateReference':rm.get('crs') or 'not established','units':', '.join(x or 'not established' for x in (rm.get('units') or [])) or 'not established','spatialCoverage':'not established — review official label and footprint','temporalCoverage':'not established — review official label','processingSteps':['Original file copied/downloaded without transformation','SHA-256 re-verified at manifest creation'],'qualityFlags':[],'uncertaintyDescription':'not established — review product documentation','humanReview':report['review'],'status':'pending-human-review','warning':'Provenance record only; not approved for scientific scoring.'}
 MANIFESTS.mkdir(parents=True,exist_ok=True); out=MANIFESTS/f'{a.dataset_id}-{report["sha256"][:12]}.json'
 if out.exists(): raise FileExistsError(f'Refusing to overwrite {out}')
 out.write_text(json.dumps(obj,indent=2),encoding='utf8'); print(json.dumps({'manifest':str(out.relative_to(ROOT)),'status':obj['status']},indent=2))
def main():
 p=argparse.ArgumentParser(description='TERRASCAN controlled planetary data ingestion'); s=p.add_subparsers(dest='cmd',required=True)
 d=s.add_parser('download'); d.add_argument('--dataset-id',choices=CATALOG,required=True); d.add_argument('--url',required=True); d.add_argument('--filename'); d.add_argument('--expected-sha256'); d.add_argument('--max-bytes',type=int,default=20*1024**3); d.add_argument('--timeout',type=int,default=60); d.set_defaults(func=download)
 i=s.add_parser('inspect'); i.add_argument('file'); i.add_argument('--dataset-id',choices=CATALOG,required=True); i.set_defaults(func=inspect)
 m=s.add_parser('manifest'); m.add_argument('inspection'); m.add_argument('--dataset-id',choices=CATALOG,required=True); m.add_argument('--source-url',required=True); m.add_argument('--source-title'); m.add_argument('--provider',required=True); m.add_argument('--product-version'); m.add_argument('--retrieved-at'); m.set_defaults(func=create_manifest)
 a=p.parse_args()
 try:a.func(a)
 except Exception as e: print(f'ERROR: {type(e).__name__}: {e}',file=sys.stderr); sys.exit(1)
if __name__=='__main__': main()
