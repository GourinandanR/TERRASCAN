# Stage 29 — Integrated Scientific Validation & System QA

## Commands
Run structural QA:
```bash
python scripts/terrascan_qa.py project
python scripts/terrascan_qa.py project --output data/qa/project-audit.json
```
Verify files against a supplied artifact manifest:
```bash
python scripts/terrascan_qa.py integrity path/to/artifact-manifest.json
```
Manifest format: `{"artifacts":[{"path":"relative/or/absolute/file","sha256":"64-lowercase-hex"}]}`. Relative paths resolve from the manifest's directory. The command detects missing files and hash mismatches; it does not certify the source's scientific validity.

Run tests:
```bash
python -m unittest scripts.test_terrascan_qa -v
python -m unittest scripts.test_terrascan_rank_sites scripts.test_terrascan_predict scripts.test_terrascan_ml scripts.test_terrascan_analog_discovery scripts.test_terrascan_classify scripts.test_terrascan_spatial scripts.test_terrascan_validate scripts.test_terrascan_pds scripts.test_terrascan_label scripts.test_terrascan_pipeline scripts.test_terrascan_features -v
cd backend && python -m pytest -q -p no:cacheprovider tests/test_api.py
```

## Scope
The project audit checks required module/document presence, package version and command registration, frontend stage sections, backend route presence, Python syntax, regression-test presence and selected ranking safeguards. The integrity command verifies supplied file hashes.

## Limitations
This is structural/static QA, not scientific validation, security certification, UI end-to-end testing, geospatial correctness certification, model generalization validation or mission readiness. A hash proves byte identity relative to the supplied digest only. Review all scientific assumptions, source product labels, units, coordinate frames, uncertainty and domain transfer independently.
