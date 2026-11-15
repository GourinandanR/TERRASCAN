#!/usr/bin/env node
/**
 * TERRASCAN local dataset inspector. Uses Node built-ins only.
 * Supports metadata extraction from ENVI headers and basic TIFF headers;
 * PDS labels are retained as text for manual review rather than guessed.
 */
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import { basename, extname, resolve } from 'node:path';

const args = process.argv.slice(2);
const fileArg = args.find((arg) => !arg.startsWith('--'));
const headerIndex = args.indexOf('--header');
const headerArg = headerIndex >= 0 ? args[headerIndex + 1] : undefined;
if (!fileArg) {
  console.error('Usage: node scripts/inspect-dataset.mjs <raster-file> [--header <metadata-file>]');
  process.exit(2);
}

const filePath = resolve(fileArg);
const fileBytes = await readFile(filePath);
const fileStat = await stat(filePath);
const sha256 = createHash('sha256').update(fileBytes).digest('hex');
const extension = extname(filePath).toLowerCase();
const result = {
  inspector: 'TERRASCAN local dataset inspector',
  inspectorVersion: '1.0.0',
  inspectedAt: new Date().toISOString(),
  file: basename(filePath),
  sizeBytes: fileStat.size,
  sha256,
  detectedFormat: 'unknown',
  metadata: {},
  warnings: [],
};

function parseEnvi(text) {
  const fields = {};
  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^\s*([^=]+?)\s*=\s*(.*)\s*$/);
    if (match) fields[match[1].trim().toLowerCase()] = match[2].trim();
  }
  const mapInfo = fields['map info']?.replace(/^\{|\}$/g, '').split(',').map((part) => part.trim());
  const bandNames = fields['band names']?.replace(/^\{|\}$/g, '').split(',').map((part) => part.trim());
  return {
    samples: Number(fields.samples) || null,
    lines: Number(fields.lines) || null,
    bands: Number(fields.bands) || null,
    dataTypeCode: Number(fields['data type']) || null,
    interleave: fields.interleave ?? null,
    byteOrder: fields['byte order'] ?? null,
    coordinateSystem: fields['coordinate system string'] ?? null,
    mapInfo: mapInfo ?? null,
    pixelSize: mapInfo?.length >= 7 ? { x: Number(mapInfo[5]), y: Number(mapInfo[6]) } : null,
    bandNames: bandNames ?? null,
    noDataValue: fields['data ignore value'] ?? null,
    rawHeaderFields: fields,
  };
}

function parseTiff(buffer) {
  if (buffer.length < 8) return null;
  const marker = buffer.toString('ascii', 0, 2);
  if (marker !== 'II' && marker !== 'MM') return null;
  const little = marker === 'II';
  const u16 = (offset) => little ? buffer.readUInt16LE(offset) : buffer.readUInt16BE(offset);
  const u32 = (offset) => little ? buffer.readUInt32LE(offset) : buffer.readUInt32BE(offset);
  const magic = u16(2);
  if (magic === 43) return { bigTiff: true, byteOrder: marker, note: 'BigTIFF detected; detailed IFD parsing is not implemented.' };
  if (magic !== 42) return null;
  const ifdOffset = u32(4);
  if (ifdOffset + 2 > buffer.length) return { byteOrder: marker, warning: 'TIFF IFD offset is outside the file.' };
  const count = u16(ifdOffset);
  const tags = {};
  const typeBytes = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8 };
  for (let i = 0; i < count; i += 1) {
    const offset = ifdOffset + 2 + i * 12;
    if (offset + 12 > buffer.length) break;
    const tag = u16(offset); const type = u16(offset + 2); const n = u32(offset + 4);
    const bytes = (typeBytes[type] ?? 0) * n;
    let valueOffset = bytes <= 4 ? offset + 8 : u32(offset + 8);
    if (valueOffset + Math.min(bytes, 16) > buffer.length) continue;
    const readValue = () => {
      if (type === 3) return n === 1 ? u16(valueOffset) : Array.from({ length: Math.min(n, 16) }, (_, j) => u16(valueOffset + j * 2));
      if (type === 4) return n === 1 ? u32(valueOffset) : Array.from({ length: Math.min(n, 16) }, (_, j) => u32(valueOffset + j * 4));
      return null;
    };
    tags[tag] = readValue();
  }
  return {
    bigTiff: false, byteOrder: marker,
    width: tags[256] ?? null, height: tags[257] ?? null,
    bitsPerSample: tags[258] ?? null, compression: tags[259] ?? null,
    photometricInterpretation: tags[262] ?? null, samplesPerPixel: tags[277] ?? 1,
    sampleFormat: tags[339] ?? null,
    georeferencing: 'GeoTIFF keys and tiepoints are not decoded by this lightweight inspector; use GDAL for authoritative CRS/geotransform inspection.',
  };
}

if (extension === '.hdr') {
  result.detectedFormat = 'ENVI header';
  result.metadata = parseEnvi(fileBytes.toString('utf8'));
} else if (['.lbl', '.xml', '.txt'].includes(extension) || fileBytes.toString('utf8', 0, Math.min(fileBytes.length, 64)).includes('PDS_VERSION_ID')) {
  const text = fileBytes.toString('utf8');
  if (/PDS_VERSION_ID|^\s*<?xml/i.test(text)) {
    result.detectedFormat = 'PDS label or XML metadata';
    result.metadata = { textPreview: text.slice(0, 12000), truncated: text.length > 12000 };
  }
} else {
  const tiff = parseTiff(fileBytes);
  if (tiff) {
    result.detectedFormat = 'TIFF/GeoTIFF';
    result.metadata = tiff;
    result.warnings.push('A TIFF signature does not prove valid georeferencing; inspect CRS, datum, scale and tiepoints with GDAL or the product label.');
  } else if (extension === '.img' || extension === '.dat') {
    result.detectedFormat = 'binary raster (unclassified)';
    result.warnings.push('Binary raster dimensions, datatype, byte order and projection require the corresponding product label/header.');
  }
}

if (headerArg) {
  const headerPath = resolve(headerArg);
  const headerText = await readFile(headerPath, 'utf8');
  result.companionHeader = { file: basename(headerPath), sha256: createHash('sha256').update(headerText).digest('hex') };
  if (extname(headerPath).toLowerCase() === '.hdr') result.metadata.companionEnviHeader = parseEnvi(headerText);
  else result.metadata.companionLabelPreview = headerText.slice(0, 12000);
}
if (result.detectedFormat === 'unknown') result.warnings.push('Format not recognized. Preserve the file and consult the source product documentation; do not infer units or projection.');
console.log(JSON.stringify(result, null, 2));
