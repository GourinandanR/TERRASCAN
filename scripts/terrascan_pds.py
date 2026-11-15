#!/usr/bin/env python3
"""TERRASCAN NASA PDS Search API client: discover metadata, never auto-approve data."""
from __future__ import annotations
import argparse, hashlib, json, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"pds-search"
BASE="https://pds.nasa.gov/api/search/1"

def fetch_json(url: str, timeout: int=45):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"TERRASCAN-PDS-discovery/2.1"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        if r.status!=200: raise RuntimeError(f"PDS API returned HTTP {r.status}")
        raw=r.read(25*1024*1024+1)
    if len(raw)>25*1024*1024: raise ValueError("PDS response exceeds 25 MiB safety limit")
    return json.loads(raw.decode("utf-8")),raw

def normalize_product(obj):
    # Preserve full API record; these common fields are convenience hints only.
    def first(*keys):
        for key in keys:
            value=obj.get(key)
            if isinstance(value,list) and value: value=value[0]
            if value not in (None,""): return value
        return None
    return {
      "lid":first("lid","pds:Identification_Area.pds:logical_identifier"),
      "lidvid":first("lidvid","pds:Identification_Area.pds:logical_identifier_version_id"),
      "title":first("title","pds:Identification_Area.pds:title"),
      "product_class":first("product_class","pds:Identification_Area.pds:product_class"),
      "start_time":first("pds:Time_Coordinates.pds:start_date_time"),
      "stop_time":first("pds:Time_Coordinates.pds:stop_date_time"),
      "raw_record":obj
    }

def save_snapshot(kind,request_url,payload,raw):
    OUT.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(raw).hexdigest()
    record={"schema_version":"1.0","provider":"NASA Planetary Data System Search API",
      "api_base":BASE,"request_url":request_url,"retrieved_at":datetime.now(timezone.utc).isoformat(),
      "response_sha256":digest,"record_count":len(payload.get("data",[])) if isinstance(payload,dict) else None,
      "normalized_products":[normalize_product(x) for x in payload.get("data",[]) if isinstance(x,dict)] if isinstance(payload,dict) else [],
      "api_response":payload,
      "limitations":["Search API coverage may be incomplete; an empty result does not prove no archive product exists.",
        "Search results are metadata discovery, not downloaded science data or validation.",
        "Product file locations and labels must be inspected independently; no records are automatically approved."]}
    path=OUT/f"{kind}-{digest[:16]}.json"
    if path.exists(): raise FileExistsError(f"Refusing to overwrite existing snapshot: {path}")
    path.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"snapshot":str(path.relative_to(ROOT)),"record_count":record["record_count"],
      "response_sha256":digest,"status":"metadata-discovery-only"},indent=2))

def search(args):
    params={"limit":str(args.limit)}
    if args.keywords: params["keywords"]=args.keywords
    if args.query: params["q"]=args.query
    if args.product_class: params["product_class"]=args.product_class
    if not (args.keywords or args.query): raise ValueError("Provide --keywords or --query")
    url=BASE+"/products?"+urllib.parse.urlencode(params)
    payload,raw=fetch_json(url,args.timeout)
    save_snapshot("search",url,payload,raw)

def resolve(args):
    identifier=args.identifier
    if not identifier.startswith("urn:"): raise ValueError("Identifier must be a PDS logical identifier beginning urn:")
    url=BASE+"/products/"+urllib.parse.quote(identifier,safe=":._-")
    payload,raw=fetch_json(url,args.timeout)
    save_snapshot("resolve",url,payload,raw)

def main():
    p=argparse.ArgumentParser(description="Discover NASA PDS product metadata without downloading or approving science files.")
    sub=p.add_subparsers(dest="command",required=True)
    s=sub.add_parser("search"); s.add_argument("--keywords"); s.add_argument("--query"); s.add_argument("--product-class")
    s.add_argument("--limit",type=int,default=20); s.add_argument("--timeout",type=int,default=45); s.set_defaults(func=search)
    r=sub.add_parser("resolve"); r.add_argument("identifier"); r.add_argument("--timeout",type=int,default=45); r.set_defaults(func=resolve)
    args=p.parse_args()
    if getattr(args,"limit",1)<1 or getattr(args,"limit",1)>200: p.error("--limit must be between 1 and 200")
    try: args.func(args)
    except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError,json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}",file=sys.stderr); sys.exit(1)
if __name__=="__main__": main()
