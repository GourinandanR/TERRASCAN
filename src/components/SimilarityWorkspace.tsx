import { useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, Database, Info, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { analogSites } from "../data/analogSites";
import { scienceEvidence, targetReferences } from "../data/scienceEvidence";
import { criterionDefinitions, defaultWeights, normalizeWeights } from "../science/criteria";
import { assessAnalog } from "../science/scoring";
import type { PlanetaryTarget } from "../science/types";

export default function SimilarityWorkspace() {
  const [target, setTarget] = useState<PlanetaryTarget>("Mars");
  const [rawWeights, setRawWeights] = useState<Record<string, number>>(defaultWeights);
  const weights = useMemo(() => normalizeWeights(rawWeights), [rawWeights]);
  const assessments = useMemo(() => analogSites.map((site) => assessAnalog({
    siteId: site.id,
    target,
    evidence: scienceEvidence,
    references: targetReferences,
    weights,
  })), [target, weights]);

  return (
    <div className="similarity-workspace">
      <section className="notice-bar similarity-notice">
        <div className="notice-icon"><ShieldCheck size={17}/></div>
        <div><strong>Evidence-gated scoring is active</strong><span>Scores remain withheld until every required criterion has compatible, traceable evidence and a target reference profile.</span></div>
        <span className="notice-tag">STAGE 5</span>
      </section>

      <section className="metric-grid similarity-metrics">
        <Metric icon={<Database size={17}/>} label="EVIDENCE RECORDS" value={String(scienceEvidence.length).padStart(2,"0")} detail="Source-verified entries"/>
        <Metric icon={<BarChart3 size={17}/>} label="REFERENCE PROFILES" value={String(targetReferences.filter((item) => item.target === target).length).padStart(2,"0")} detail={`${target} reference criteria`}/>
        <Metric icon={<AlertTriangle size={17}/>} label="SCORES ISSUED" value="00" detail="No complete evidence sets"/>
        <Metric icon={<CheckCircle2 size={17}/>} label="CANDIDATES" value={String(analogSites.length).padStart(2,"0")} detail="Awaiting evidence"/>
      </section>

      <section className="similarity-main-grid">
        <div className="panel similarity-panel">
          <div className="panel-header">
            <div><div className="panel-kicker">COMPARISON CONFIGURATION</div><h2>Target reference environment</h2></div>
            <span className="step-number">05</span>
          </div>
          <div className="target-selector">
            <label htmlFor="similarity-target">PLANETARY TARGET</label>
            <select id="similarity-target" value={target} onChange={(event) => setTarget(event.target.value as PlanetaryTarget)}>
              <option value="Mars">Mars</option><option value="Moon">Moon</option>
            </select>
          </div>
          <div className="criteria-heading"><div><strong>Scientific comparison criteria</strong><small>Weights are configurable research assumptions, not validated scientific priorities.</small></div><span>WEIGHT</span></div>
          <div className="criteria-list">
            {criterionDefinitions.map((criterion) => (
              <div className="criterion-control" key={criterion.id}>
                <div className="criterion-top"><div><strong>{criterion.label}</strong><small>{criterion.description}</small></div><b>{(weights[criterion.id] * 100).toFixed(1)}%</b></div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={rawWeights[criterion.id] * 100}
                  aria-label={`${criterion.label} weight`}
                  onChange={(event) => setRawWeights((current) => ({ ...current, [criterion.id]: Number(event.target.value) / 100 }))}
                />
                <div className="criterion-foot"><span>{criterion.category.toUpperCase()}</span><span>{criterion.required ? "REQUIRED" : "OPTIONAL"} · {criterion.method.toUpperCase()}</span></div>
              </div>
            ))}
          </div>
          <div className="weight-total"><span>Normalized total weight</span><strong>100.0%</strong></div>
          <div className="model-note"><Info size={14}/><span>Weights are normalized automatically. Changing a weight changes the future scoring model; it does not create evidence or produce a score.</span></div>
        </div>

        <div className="panel assessment-panel">
          <div className="panel-header"><div><div className="panel-kicker">CANDIDATE ASSESSMENTS</div><h2>{target} analog comparison</h2></div><span className="candidate-indicator">EVIDENCE STATUS</span></div>
          <div className="assessment-legend"><span><i className="legend-dot cyan"/> Evidence-backed</span><span><i className="legend-dot muted"/> Not assessed</span></div>
          <div className="assessment-list">
            {assessments.map((assessment) => {
              const site = analogSites.find((item) => item.id === assessment.siteId)!;
              return <article className="assessment-card" key={assessment.siteId}>
                <div className="assessment-card-head"><div><strong>{site.name}</strong><small>{site.region}</small></div><span className="withheld-tag">SCORE WITHHELD</span></div>
                <div className="assessment-values">
                  <div><span>SIMILARITY</span><strong>—</strong></div>
                  <div><span>COMPLETENESS</span><strong>{assessment.dataCompleteness}%</strong></div>
                  <div><span>CONFIDENCE</span><strong>—</strong></div>
                </div>
                <div className="completeness-track"><i style={{ width: `${assessment.dataCompleteness}%` }}/></div>
                <div className="assessment-foot"><span>{assessment.missingRequired.length} required criteria missing</span><span>Mission suitability: not assessed</span></div>
              </article>;
            })}
          </div>
          <div className="withheld-explanation"><AlertTriangle size={15}/><div><strong>No scientific scores have been generated.</strong><span>There are currently no source-verified evidence records or planetary target reference profiles in the project data registry.</span></div></div>
        </div>
      </section>

      <section className="panel framework-panel">
        <div className="panel-header"><div><div className="panel-kicker">ASSESSMENT MODEL</div><h2>Four independent outputs</h2></div><SlidersHorizontal size={18} className="muted-icon"/></div>
        <div className="output-grid">
          <Output title="Similarity" value="WITHHELD" detail="Weighted criterion comparison. Requires all required evidence/reference pairs."/>
          <Output title="Data completeness" value="0%" detail="Share of required criteria with compatible evidence and reference values."/>
          <Output title="Confidence" value="N/A" detail="Evidence quality and target comparability, independent of similarity."/>
          <Output title="Mission suitability" value="NOT ASSESSED" detail="Separate pass/fail/unknown operational gates defined by mission requirements."/>
        </div>
      </section>

      <section className="panel framework-panel">
        <div className="panel-header"><div><div className="panel-kicker">EVIDENCE REQUIREMENTS</div><h2>What each criterion needs</h2></div><Database size={18} className="muted-icon"/></div>
        <div className="evidence-guidance-grid">
          {criterionDefinitions.map((criterion) => <div className="guidance-item" key={criterion.id}><strong>{criterion.label}</strong><span>{criterion.evidenceGuidance}</span><small>{criterion.unit} · {criterion.method}</small></div>)}
        </div>
      </section>
    </div>
  );
}

function Metric({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return <div className="panel metric-card"><div className="metric-top"><span className="metric-icon">{icon}</span><span className="metric-label">{label}</span></div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function Output({ title, value, detail }: { title: string; value: string; detail: string }) {
  return <div className="output-item"><span>{title}</span><strong>{value}</strong><p>{detail}</p></div>;
}
