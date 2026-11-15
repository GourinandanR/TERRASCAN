#!/usr/bin/env python3
"""TERRASCAN Stage 22: conservative planetary raster and PDS label validation."""
from __future__ import annotations
import argparse, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'data' / 'validation'
BODY_ALIASES = {'earth': {'earth'}, 'moon': {'moon', 'luna'}, 'mars': {'mars'}}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1].lower()

def label_metadata(path: Path) -> dict:
    root = ET.parse(path).getroot()
    result = {}
    wanted = {'name', 'value', 'unit', 'units', 'longitude_direction', 'latitude_type',
              'coordinate_space_reference', 'reference_frame', 'body_fixed_coordinate_system',
              'planetary_reference_frame', 'target_name', 'body_name', 'horizontal_cs_name',
              'horizontal_coordinate_system_name', 'map_projection_name', 'pixel_resolution_x',
              'pixel_resolution_y', 'line_count', 'sample_count', 'minimum', 'maximum',
              'missing_constant', 'scaling_factor', 'value_offset'}
    # Retain compact element records so context is not lost when PDS4 uses repeated <name>/<value>.
    for el in root.iter():
        n = local_name(el.tag)
        if n in wanted and el.text and el.text.strip():
            result.setdefault(n, []).append(el.text.strip())
        # PDS4 often encodes values as generic <name> elements inside typed containers.
        if n == 'name' and el.text and el.text.strip():
            parent = next((p for p in root.iter() if el in list(p)), None)
            parent_name = local_name(parent.tag) if parent is not None else ''
            value = el.text.strip()
            if 'target' in parent_name:
                result.setdefault('target_name', []).append(value)
            if 'coordinate_system' in parent_name or 'reference_frame' in parent_name:
                result.setdefault('horizontal_coordinate_system_name', []).append(value)
    return result

def label_values(meta: dict, *keys: str) -> list[str]:
    vals = []
    for key in keys: vals.extend(meta.get(key, []))
    return vals

def check(code, status, message, observed=None):
    item = {'rule': code, 'status': status, 'message': message}
    if observed is not None: item['observed'] = observed
    return item

def validate(inspection: dict, expected_body: str, label_path: Path | None = None) -> dict:
    expected = expected_body.strip().lower()
    if expected not in BODY_ALIASES:
        raise ValueError('expected body must be Earth, Moon, or Mars')
    checks = []
    body = str(inspection.get('body') or inspection.get('targetBody') or '').strip().lower()
    if body in BODY_ALIASES[expected]:
        checks.append(check('BODY_EXPECTED', 'pass', 'Inspection body matches requested body.', body))
    elif body:
        checks.append(check('BODY_EXPECTED', 'fail', 'Inspection body conflicts with requested body; no conversion is attempted.', body))
    else:
        checks.append(check('BODY_EXPECTED', 'unknown', 'Inspection does not declare a target body.'))

    raster = inspection.get('rasterMetadata') or {}
    if raster.get('error'):
        checks.append(check('RASTER_READ', 'fail', 'Raster metadata inspection reported an error.', raster['error']))
    elif raster.get('available') is False:
        checks.append(check('RASTER_READ', 'unknown', 'Rasterio metadata is unavailable; install optional geo dependencies.'))
    elif raster.get('available') is True:
        checks.append(check('RASTER_READ', 'pass', 'Raster metadata was read; this does not establish scientific validity.'))
        width, height, bands = raster.get('width'), raster.get('height'), raster.get('bandCount')
        if all(isinstance(v, int) and v > 0 for v in (width, height, bands)):
            checks.append(check('RASTER_DIMENSIONS', 'pass', 'Raster dimensions and band count are positive.', {'width': width, 'height': height, 'bands': bands}))
        else:
            checks.append(check('RASTER_DIMENSIONS', 'fail', 'Raster dimensions or band count are missing or non-positive.'))
        res = raster.get('resolution')
        if isinstance(res, list) and len(res) >= 2 and all(isinstance(v, (int,float)) and math.isfinite(v) and v != 0 for v in res[:2]):
            checks.append(check('RASTER_RESOLUTION', 'pass', 'Pixel resolution values are finite and non-zero; units still require verification.', res[:2]))
        else:
            checks.append(check('RASTER_RESOLUTION', 'fail', 'Pixel resolution is missing, zero, or invalid.', res))
        bounds = raster.get('bounds')
        if isinstance(bounds, list) and len(bounds) == 4 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in bounds) and bounds[0] < bounds[2] and bounds[1] < bounds[3]:
            checks.append(check('SPATIAL_BOUNDS', 'pass', 'Raster bounds are finite and ordered in the reported coordinate system.', bounds))
        else:
            checks.append(check('SPATIAL_BOUNDS', 'fail', 'Raster bounds are missing, non-finite, or degenerate.', bounds))
        crs = raster.get('crs')
        if crs:
            checks.append(check('CRS_DECLARED', 'pass', 'A CRS string is declared; scientific body/frame compatibility is not established.', crs))
            crs_text = str(crs).lower()
            if expected != 'earth' and any(x in crs_text for x in ('epsg:4326','epsg:3857','wgs 84','web mercator')):
                checks.append(check('PLANETARY_CRS_GUARD', 'fail', 'Earth-centric CRS detected for a non-Earth target. Verify the authoritative planetary frame; no reprojection was performed.', crs))
            else:
                checks.append(check('PLANETARY_CRS_GUARD', 'unknown', 'CRS text alone cannot prove the correct planetary body-fixed frame or longitude convention.', crs))
        else:
            checks.append(check('CRS_DECLARED', 'unknown', 'No CRS is declared in raster metadata.'))
        units = raster.get('units')
        if units and any(str(x).strip() for x in units):
            checks.append(check('UNITS_DECLARED', 'pass', 'Band unit metadata is present; semantic correctness requires label review.', units))
        else:
            checks.append(check('UNITS_DECLARED', 'unknown', 'Band units are absent; units will not be inferred from pixel values.'))
        nodata = raster.get('nodataValues')
        checks.append(check('NODATA_METADATA', 'pass' if nodata and any(x is not None for x in nodata) else 'unknown', 'No-data metadata is declared.' if nodata and any(x is not None for x in nodata) else 'No-data metadata is absent; pixel-level quality was not evaluated.', nodata))
    else:
        checks.append(check('RASTER_READ', 'unknown', 'Inspection contains no usable raster metadata.'))

    if label_path:
        try:
            meta = label_metadata(label_path)
            checks.append(check('PDS_LABEL_PARSE', 'pass', 'XML label parsed; extracted fields are not independently authenticated.'))
            targets = label_values(meta, 'target_name','body_name')
            if targets:
                norm = {x.strip().lower() for x in targets}
                expected_aliases = BODY_ALIASES[expected]
                checks.append(check('LABEL_TARGET_BODY', 'pass' if any(any(a == v or a in v for a in expected_aliases) for v in norm) else 'fail', 'Label target field compared with requested body.', targets))
            else:
                checks.append(check('LABEL_TARGET_BODY', 'unknown', 'PDS label has no recognized target/body field.'))
            frame = label_values(meta, 'reference_frame','body_fixed_coordinate_system','planetary_reference_frame','horizontal_cs_name','horizontal_coordinate_system_name','coordinate_space_reference')
            checks.append(check('LABEL_REFERENCE_FRAME', 'pass' if frame else 'unknown', 'Coordinate-frame text found; verify against product documentation.' if frame else 'No recognized coordinate-frame field found in label.', frame or None))
            units = label_values(meta, 'unit','units')
            checks.append(check('LABEL_UNITS', 'pass' if units else 'unknown', 'Unit declarations found in label; verify the correct field semantics.' if units else 'No unit declaration found in recognized label fields.', units or None))
        except Exception as exc:
            checks.append(check('PDS_LABEL_PARSE', 'fail', f'Could not parse supplied label: {type(exc).__name__}: {exc}'))
    else:
        checks.append(check('PDS_LABEL_PARSE', 'unknown', 'No PDS label supplied; label-to-raster cross-check was not possible.'))

    statuses = {x['status'] for x in checks}
    overall = 'fail' if 'fail' in statuses else ('review-required' if 'unknown' in statuses else 'checks-passed')
    source_hash = inspection.get('sha256')
    return {'schemaVersion':'1.0','validator':'TERRASCAN Stage 22','expectedBody':expected_body,
            'generatedAt':datetime.now(timezone.utc).isoformat(),'inspectionSourceHash':source_hash,
            'labelFile':str(label_path) if label_path else None,
            'labelSha256':digest(label_path) if label_path and label_path.is_file() else None,
            'checks':checks,'summary':{'overall':overall,'pass':sum(x['status']=='pass' for x in checks),
            'warning':sum(x['status']=='warning' for x in checks),'unknown':sum(x['status']=='unknown' for x in checks),
            'fail':sum(x['status']=='fail' for x in checks)},
            'scientificDisposition':'not-approved','evidenceApproval':'unchanged',
            'limitations':['Metadata checks do not establish scientific correctness or product authenticity.',
             'A recognized CRS does not prove the correct planetary body-fixed frame, datum, axis order or longitude convention.',
             'No coordinate transformation, unit conversion, resampling, no-data masking or pixel-level quality assessment is performed.',
             'Missing units and coordinate metadata are not inferred from numeric values.',
             'A human reviewer must compare the complete authoritative PDS label and product documentation before use.']}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inspection', help='Stage 8 inspection JSON')
    ap.add_argument('--expected-body', required=True, choices=['Earth','Moon','Mars'])
    ap.add_argument('--label', help='Optional PDS4 XML label')
    ap.add_argument('--output', help='Optional output JSON path')
    a=ap.parse_args(); ip=Path(a.inspection).resolve(); data=json.loads(ip.read_text(encoding='utf8'))
    lp=Path(a.label).resolve() if a.label else None
    report=validate(data,a.expected_body,lp)
    if a.output: out=Path(a.output).resolve()
    else:
        REPORTS.mkdir(parents=True,exist_ok=True); out=REPORTS/f'{ip.stem}-{a.expected_body.lower()}-validation.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists(): raise FileExistsError(f'Refusing to overwrite existing validation report: {out}')
    out.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({'report':str(out),'overall':report['summary']['overall'],'summary':report['summary'],'scientificDisposition':report['scientificDisposition']},indent=2))
    return 1 if report['summary']['fail'] else 0
if __name__=='__main__': raise SystemExit(main())
