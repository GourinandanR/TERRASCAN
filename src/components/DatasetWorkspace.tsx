import { useMemo, useState } from "react";
import { Database, ExternalLink, FileCheck2, Filter, Info, ShieldCheck } from "lucide-react";
import { datasetCatalog, datasetStatusLabel } from "../data/datasetCatalog";
import { ingestionManifests } from "../data/ingestionManifests";

const targets = ["All", "Moon", "Mars"] as const;
const criteria = ["All", "terrain", "thermal", "geology"] as const;

export default function DatasetWorkspace() {
  const [target, setTarget] = useState<(typeof targets)[number]>("All");
  const [criterion, setCriterion] = useState<(typeof criteria)[number]>("All");
  const [selectedId, setSelectedId] = useState(datasetCatalog[0]?.id ?? "");
  const filtered = useMemo(() => datasetCatalog.filter((item) =>
    (target === "All" || item.target === target) &&
    (criterion === "All" || item.criterion === criterion)
  ), [target, criterion]);
  const selected = datasetCatalog.find((item) => item.id === selectedId) ?? filtered[0] ?? null;

  return (
    <div className="dataset-workspace">
      <section className="notice-bar">
        <div className="notice-icon"><ShieldCheck size={17}/></div>
        <div><strong>Catalogued sources are not yet ingested datasets</strong><span>The catalogue identifies official archive entry points. Stage 7 adds a local inspector and evidence-traceability checks; no source raster has yet been downloaded or used for scoring.</span></div>
        <span className="notice-tag">STAGE 7</span>
      </section>

      <section className="metric-grid">
        <Metric icon={<Database size={17}/>} label="CATALOGUED DATASETS" value={String(datasetCatalog.length).padStart(2,"0")} detail="Official source entry points"/>
        <Metric icon={<FileCheck2 size={17}/>} label="INGESTED DATASETS" value={String(ingestionManifests.length).padStart(2,"0")} detail="Checksum-verified manifests"/>
        <Metric icon={<Filter size={17}/>} label="CRITERIA COVERED" value="03" detail="Terrain · Thermal · Geology"/>
        <Metric icon={<ShieldCheck size={17}/>} label="VALIDATED PRODUCTS" value="00" detail="Awaiting local inspection"/>
      </section>

      <section className="dataset-main-grid">
        <div className="panel dataset-list-panel">
          <div className="panel-header"><div><div className="panel-kicker">SOURCE CATALOG</div><h2>Scientific datasets</h2></div><span className="candidate-indicator">{filtered.length} RECORDS</span></div>
          <div className="dataset-filters">
            <label>BODY<select value={target} onChange={(event) => setTarget(event.target.value as typeof target)}>{targets.map((value) => <option key={value}>{value}</option>)}</select></label>
            <label>CRITERION<select value={criterion} onChange={(event) => setCriterion(event.target.value as typeof criterion)}>{criteria.map((value) => <option key={value}>{value}</option>)}</select></label>
          </div>
          <div className="dataset-record-list">
            {filtered.map((item) => <button key={item.id} className={`dataset-record ${selected?.id === item.id ? "dataset-record-active" : ""}`} onClick={() => setSelectedId(item.id)}>
              <span className="dataset-record-type">{item.target.toUpperCase()} · {item.criterion.toUpperCase()}</span>
              <strong>{item.title}</strong>
              <small>{item.provider}</small>
              <span className="dataset-status">{datasetStatusLabel[item.status]}</span>
            </button>)}
            {filtered.length === 0 && <div className="empty-search">No catalog records match these filters.</div>}
          </div>
        </div>

        <aside className="panel dataset-detail-panel">
          <div className="panel-header"><div><div className="panel-kicker">DATASET PROFILE</div><h2>Source metadata</h2></div><Database size={18} className="muted-icon"/></div>
          {selected ? <>
            <span className="dataset-record-type">{selected.target.toUpperCase()} · {selected.criterion.toUpperCase()}</span>
            <h3 className="dataset-detail-title">{selected.title}</h3>
            <p className="dataset-provider">{selected.provider} · {selected.instrument}</p>
            <div className="dataset-metadata">
              <Meta label="PRODUCT TYPE" value={selected.productType}/>
              <Meta label="KNOWN RESOLUTION" value={selected.knownResolution}/>
              <Meta label="UNITS" value={selected.units}/>
              <Meta label="COORDINATE REFERENCE" value={selected.coordinateReference}/>
              <Meta label="SPATIAL COVERAGE" value={selected.spatialCoverage}/>
              <Meta label="TEMPORAL COVERAGE" value={selected.temporalCoverage}/>
            </div>
            <div className="dataset-caveats"><strong>INGESTION CHECKS</strong>{selected.caveats.map((note) => <p key={note}>• {note}</p>)}</div>
            <a className="dataset-source-link" href={selected.landingPage} target="_blank" rel="noreferrer">Open official archive / product page <ExternalLink size={13}/></a>
            {selected.accessUrl !== selected.landingPage && <a className="dataset-source-link secondary" href={selected.accessUrl} target="_blank" rel="noreferrer">Open data access page <ExternalLink size={13}/></a>}
          </> : <div className="selected-empty">Select a dataset to inspect its metadata.</div>}
        </aside>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 21 · OFFICIAL ARCHIVE DISCOVERY</div><h2>NASA Planetary Data System integration</h2></div><Database size={18} className="muted-icon"/></div>
        <p>Search PDS product metadata, resolve logical identifiers, and preserve the raw response with a SHA-256 digest. Discovery results are not scientific measurements and are never auto-approved.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_pds.py search --keywords MOLA --limit 20</span>
          <span>python scripts/terrascan_pds.py search --keywords LOLA --limit 20</span>
          <span>python scripts/terrascan_pds.py resolve urn:nasa:pds:your.product.identifier</span>
          <span>python scripts/terrascan_ingest.py download --dataset-id mars-mola-megdr --url OFFICIAL_HTTPS_FILE_URL</span>
        </div>
        <p className="dataset-policy-note">Snapshots are written to data/pds-search/. Check the official product label and choose a direct allow-listed HTTPS file URL before downloading. Cross-host redirects are rejected. NASA PDS warns that Search API coverage may be incomplete.</p>
        <a className="dataset-source-link" href="https://nasa-pds.github.io/pds-api/guides/search/endpoints.html" target="_blank" rel="noreferrer">PDS Search API documentation <ExternalLink size={13}/></a>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 22 · PLANETARY VALIDATION</div><h2>Raster and coordinate-system validation</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Generate a separate validation report from an existing inspection JSON. The validator checks body consistency, raster dimensions, bounds, resolution, declared CRS, units, no-data metadata and optional PDS XML label hints.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_validate.py data/inspection/INSPECTION.json --expected-body Mars --label PRODUCT.xml</span>
          <span>python scripts/terrascan_validate.py data/inspection/INSPECTION.json --expected-body Moon</span>
        </div>
        <p className="dataset-policy-note">A detected conflict is marked fail; missing metadata remains unknown and requires review. Reports never approve evidence or modify rasters. A recognized CRS is not proof of the correct planetary reference frame. See docs/backend/STAGE22_PLANETARY_VALIDATION.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 23 · MULTISCALE SPATIAL ANALYSIS</div><h2>Planetary terrain metrics</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Compute descriptive elevation distributions, topographic position index, local elevation variability and terrain-ruggedness proxies at multiple neighborhood scales. Requires a matching Stage 22 validation report.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_spatial.py path/to/DEM.tif --validation-report data/validation/DEM-mars-validation.json --body Mars --windows 3 7 15 --pixel-size-units m</span>
          <span>python scripts/terrascan_spatial.py --help</span>
        </div>
        <p className="dataset-policy-note">Pixel-spacing units must be verified from authoritative product documentation. Outputs are descriptive-only, hash-bound and immutable; they do not create analog scores, rankings or evidence approvals. See docs/backend/STAGE23_ADVANCED_GEOGRAPHIC_ANALYSIS.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 24 · SURFACE FEATURE CLASSIFICATION</div><h2>Rule-based terrain classification</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Extract slope, topographic position and local elevation variability, then assign class IDs using a transparent, operator-supplied threshold configuration.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_classify.py path/to/DEM.tif --validation-report data/validation/DEM-mars-validation.json --config path/to/reviewed-rules.json --body Mars --window 3 --pixel-size-units m --vertical-units m</span>
          <span>python scripts/terrascan_classify.py --help</span>
        </div>
        <p className="dataset-policy-note">No default scientific classes or thresholds are invented. The first matching rule in the reviewed configuration wins. Results are exploratory, pending human review, and do not change evidence approval or calculate analog similarity. See docs/backend/STAGE24_SURFACE_FEATURE_CLASSIFICATION.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 25 · PLANETARY ANALOG DISCOVERY</div><h2>Evidence-gated analog retrieval</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Compare approved Moon/Mars target feature profiles against approved Earth candidate features using explainable weighted nearest-neighbour scoring.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_analog_discovery.py path/to/approved-analog-input.json</span>
          <span>python scripts/terrascan_analog_discovery.py --help</span>
        </div>
        <p className="dataset-policy-note">Requires complete, unit-compatible, approved observations and approved source manifests. Weights and tolerances must be scientifically justified. This is not a trained ML model; results are exploratory and do not assess mission suitability. See docs/backend/STAGE25_ANALOG_DISCOVERY.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 26 · SUPERVISED ML TERRAIN RECOGNITION</div><h2>Labelled terrain-pattern model</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Train an optional Random Forest classifier from operator-supplied, provenance-backed labelled terrain samples; evaluate on a stratified holdout split and run schema-matched inference.</p>
        <div className="manifest-fields">
          <span>pip install -r requirements-ml.txt</span>
          <span>python scripts/terrascan_ml.py train path/to/reviewed-labelled-samples.json --output-dir data/ml-models/run-001 --seed 42</span>
          <span>python scripts/terrascan_ml.py predict data/ml-models/run-001/model.joblib path/to/unlabelled-samples.json --output data/ml-predictions/run-001.json</span>
          <span>python -m unittest scripts.test_terrascan_ml -v</span>
        </div>
        <p className="dataset-policy-note">No labelled planetary training data or trained model is bundled. Predictions remain exploratory and pending human review. Holdout metrics do not prove cross-body or cross-sensor generalization; class probabilities are not calibrated by default. Evidence approval and mission authorization remain unchanged. See docs/backend/STAGE26_ML_TERRAIN_PATTERN_RECOGNITION.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 27 · PREDICTIVE TERRAIN ANALYSIS</div><h2>Uncertainty-aware terrain regression</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Predict an explicitly defined continuous terrain target from reviewed labelled samples. Independent spatial groups are separated for training, interval calibration and testing.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_predict.py train path/to/reviewed-target-samples.json --output-dir data/predictive-models/run-001 --seed 42 --trees 400 --coverage 0.90</span>
          <span>python scripts/terrascan_predict.py predict data/predictive-models/run-001/regressor.joblib path/to/unlabelled-features.json --output data/predictive-results/run-001.json</span>
          <span>python -m unittest scripts.test_terrascan_predict -v</span>
        </div>
        <p className="dataset-policy-note">Requires independently grouped, provenance-backed labels and an explicit target unit. Residual-calibrated intervals are approximate and may fail under distribution shift. No model or planetary training data is bundled; predictions remain pending human review. See docs/backend/STAGE27_PREDICTIVE_TERRAIN_ANALYSIS.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 28 · MISSION-SITE RANKING</div><h2>Evidence-gated site shortlist</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Combine Stage 25 analog discovery reports with Stage 17 mission-constraint assessments. Eligible sites receive a transparent policy-weighted utility; incomplete or ineligible sites are withheld with explicit reasons.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_rank_sites.py path/to/ranking-input.json --output data/site-ranking/review-001.json</span>
          <span>python -m unittest scripts.test_terrascan_rank_sites -v</span>
        </div>
        <p className="dataset-policy-note">Requires matching site IDs, a ranked approved-evidence analog result, an eligible suitability snapshot with approved evidence, and an operator-supplied uncertainty fraction. Ranking weights are policy choices, not scientific truths. No site is selected or authorized. See docs/backend/STAGE28_INTELLIGENT_MISSION_SITE_RANKING.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">STAGE 29 · INTEGRATED SCIENTIFIC QA</div><h2>Project and evidence integrity audit</h2></div><ShieldCheck size={18} className="muted-icon"/></div>
        <p>Run structural checks across required modules, documentation, commands, backend routes, Python syntax and regression-test coverage. Verify supplied artifact files against SHA-256 manifests.</p>
        <div className="manifest-fields">
          <span>python scripts/terrascan_qa.py project</span>
          <span>python scripts/terrascan_qa.py project --output data/qa/project-audit.json</span>
          <span>python scripts/terrascan_qa.py integrity path/to/artifact-manifest.json</span>
          <span>python -m unittest scripts.test_terrascan_qa -v</span>
        </div>
        <p className="dataset-policy-note">This is structural/static QA and byte-integrity verification, not scientific validation, security certification, UI end-to-end testing or mission readiness. See docs/backend/STAGE29_INTEGRATED_SCIENTIFIC_QA.md.</p>
      </section>

      <section className="panel ingestion-policy-panel">
        <div className="panel-header"><div><div className="panel-kicker">REPRODUCIBLE INGESTION</div><h2>Validated ingestion before a dataset can be scored</h2></div><Info size={18} className="muted-icon"/></div>
        <div className="manifest-fields">
          {["Dataset ID and official source URL","Retrieval timestamp and SHA-256 checksum","Product version and file format","CRS / map projection and spatial resolution","Units, spatial extent and temporal coverage","Processing steps and software versions","Quality flags, uncertainty and operator notes"].map((item) => <span key={item}>{item}</span>)}
        </div>
        <p className="dataset-policy-note">Run `node scripts/inspect-dataset.mjs &lt;file&gt; [--header &lt;label-or-header&gt;]` to create a first-pass inspection report and SHA-256 digest. Review the official product label and verify CRS, units, scale/offset, no-data, uncertainty and quality flags before creating a manifest. The lightweight inspector is not a substitute for GDAL/Rasterio or PDS tools; browse maps and screenshots are not quantitative rasters.</p>
      </section>
    </div>
  );
}

function Metric({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail: string }) {
  return <div className="panel metric-card"><div className="metric-top"><span className="metric-icon">{icon}</span><span className="metric-label">{label}</span></div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}
function Meta({ label, value }: { label: string; value: string }) {
  return <div className="dataset-meta-item"><span>{label}</span><strong>{value}</strong></div>;
}

