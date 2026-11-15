import { useMemo, useState } from "react";
import { AlertTriangle, BarChart3, FileJson, FileSpreadsheet, Info, ShieldCheck } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { analogSites } from "../data/analogSites";
import {
  comparisonFeatures, rankAnalogSites,
  type FeatureObservation, type TargetFeature,
} from "../science/analogComparison";

const observations: FeatureObservation[] = [];
const targetFeatures: TargetFeature[] = [];

const featureLabels: Record<string, string> = Object.fromEntries(
  comparisonFeatures.map((feature) => [feature.key, feature.label]),
);

function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function AnalogComparisonWorkspace() {
  const [target, setTarget] = useState<"Moon" | "Mars">("Mars");
  const [selectedSite, setSelectedSite] = useState("atacama");
  const [statusFilter, setStatusFilter] = useState<"all" | "complete" | "incomplete">("all");

  const results = useMemo(
    () => rankAnalogSites(target, observations, targetFeatures),
    [target],
  );
  const selected = results.find((item) => item.siteId === selectedSite) ?? results[0];
  const ranked = results.filter((item) => item.score !== null);
  const visibleResults = results.filter((item) => {
    if (statusFilter === "complete") return item.score !== null;
    if (statusFilter === "incomplete") return item.score === null;
    return true;
  });
  const featureCoverage = comparisonFeatures.map((feature) => {
    const matched = results.filter((result) =>
      result.featureResults.some((item) => item.feature === feature.key && item.status === "matched")
    ).length;
    return { feature: feature.label, matched, missing: results.length - matched };
  });
  const selectedSiteName = analogSites.find((site) => site.id === selectedSite)?.name ?? selectedSite;

  const exportJson = () => downloadFile(
    `terrascan-${target.toLowerCase()}-comparison-report.json`,
    JSON.stringify({
      generatedAt: new Date().toISOString(),
      target,
      model: "TERRASCAN Stage 11 comparison dashboard",
      weights: comparisonFeatures,
      candidateResults: results,
      observationsCount: observations.length,
      targetReferencesCount: targetFeatures.length,
      interpretation: "No rankings are issued unless all configured feature pairs are present and compatible.",
    }, null, 2),
    "application/json",
  );

  const exportCsv = () => {
    const headers = ["siteId", "siteName", "target", "rank", "similarity", "coveragePercent", "confidence", ...comparisonFeatures.map((f) => `${f.key}_status`), ...comparisonFeatures.map((f) => `${f.key}_similarity`)];
    const rows = results.map((result) => {
      const site = analogSites.find((item) => item.id === result.siteId)!;
      const byFeature = new Map(result.featureResults.map((item) => [item.feature, item]));
      return [
        result.siteId, site.name, target, result.rank ?? "", result.score ?? "", result.coverage,
        result.confidence ?? "",
        ...comparisonFeatures.map((f) => byFeature.get(f.key)?.status ?? ""),
        ...comparisonFeatures.map((f) => byFeature.get(f.key)?.similarity ?? ""),
      ];
    });
    const escape = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    downloadFile(
      `terrascan-${target.toLowerCase()}-comparison-report.csv`,
      [headers, ...rows].map((row) => row.map(escape).join(",")).join("\n"),
      "text/csv;charset=utf-8",
    );
  };

  return <div className="similarity-workspace stage11-dashboard">
    <section className="notice-bar similarity-notice">
      <div className="notice-icon"><ShieldCheck size={17}/></div>
      <div><strong>Scientific dashboard · evidence-gated</strong><span>Charts display measured results only. Missing inputs are shown as unavailable, never replaced with illustrative values.</span></div>
      <span className="notice-tag">STAGE 11</span>
    </section>

    <section className="metric-grid similarity-metrics">
      <Metric label="EARTH CANDIDATES" value={String(analogSites.length).padStart(2,"0")} detail="Registered candidate regions"/>
      <Metric label="RANKINGS ISSUED" value={String(ranked.length).padStart(2,"0")} detail="Complete feature profiles"/>
      <Metric label="FEATURE OBSERVATIONS" value={String(observations.length).padStart(2,"0")} detail="Reviewed measurements"/>
      <Metric label="TARGET REFERENCES" value={String(targetFeatures.filter((item) => item.target === target).length).padStart(2,"0")} detail={`${target} reference features`}/>
    </section>

    <section className="panel stage11-controls">
      <div className="panel-header">
        <div><div className="panel-kicker">DASHBOARD CONTROLS</div><h2>Comparison scope</h2></div>
        <div className="stage11-export-actions">
          <button className="subtle-button" onClick={exportCsv}><FileSpreadsheet size={14}/> Export CSV</button>
          <button className="subtle-button" onClick={exportJson}><FileJson size={14}/> Export JSON</button>
        </div>
      </div>
      <div className="stage11-filter-row">
        <label>PLANETARY TARGET
          <select value={target} onChange={(event) => setTarget(event.target.value as "Moon" | "Mars")}>
            <option value="Mars">Mars</option><option value="Moon">Moon</option>
          </select>
        </label>
        <label>SELECT CANDIDATE
          <select value={selectedSite} onChange={(event) => setSelectedSite(event.target.value)}>
            {analogSites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
          </select>
        </label>
        <label>RANKING STATUS
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}>
            <option value="all">All candidates</option><option value="complete">Complete only</option><option value="incomplete">Incomplete only</option>
          </select>
        </label>
      </div>
    </section>

    <section className="stage11-chart-grid">
      <div className="panel stage11-chart-panel">
        <div className="panel-header"><div><div className="panel-kicker">CANDIDATE PERFORMANCE</div><h2>Similarity ranking</h2></div><BarChart3 size={18} className="muted-icon"/></div>
        {ranked.length ? (
          <div className="stage11-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ranked.map((item) => ({ name: analogSites.find((site) => site.id === item.siteId)?.name ?? item.siteId, score: item.score }))} margin={{ top: 10, right: 12, left: 0, bottom: 48 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,174,205,.12)"/>
                <XAxis dataKey="name" angle={-22} textAnchor="end" interval={0} tick={{ fill: "#91a4b6", fontSize: 10 }} axisLine={{ stroke: "#405367" }} />
                <YAxis domain={[0,100]} tick={{ fill: "#91a4b6", fontSize: 10 }} axisLine={false}/>
                <Tooltip contentStyle={{ background: "#102235", border: "1px solid rgba(139,174,205,.2)", borderRadius: 8, color: "#dce7f2" }}/>
                <Bar dataKey="score" name="Similarity %" radius={[5,5,0,0]} fill="#35c9df"/>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyChart title="No comparable rankings available" detail="The ranking chart will populate after all five feature pairs have verified observations and target references."/>}
      </div>

      <div className="panel stage11-chart-panel">
        <div className="panel-header"><div><div className="panel-kicker">DATA COMPLETENESS</div><h2>Feature coverage by dimension</h2></div><Info size={18} className="muted-icon"/></div>
        <div className="stage11-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={featureCoverage} layout="vertical" margin={{ top: 4, right: 14, left: 18, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,174,205,.12)" horizontal={false}/>
              <XAxis type="number" domain={[0, analogSites.length]} hide/>
              <YAxis type="category" dataKey="feature" width={128} tick={{ fill: "#91a4b6", fontSize: 10 }} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={{ background: "#102235", border: "1px solid rgba(139,174,205,.2)", borderRadius: 8, color: "#dce7f2" }}/>
              <Bar dataKey="matched" name="Matched candidates" stackId="a" fill="#35c9df" radius={[0,3,3,0]}/>
              <Bar dataKey="missing" name="Missing candidates" stackId="a" fill="#43566b" radius={[0,3,3,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="stage11-chart-legend"><span><i className="legend-dot cyan"/> Matched</span><span><i className="legend-dot muted"/> Missing</span></div>
      </div>
    </section>

    <section className="similarity-main-grid">
      <div className="panel assessment-panel">
        <div className="panel-header"><div><div className="panel-kicker">CANDIDATE TABLE</div><h2>Earth analog comparison status</h2></div><span className="candidate-indicator">{visibleResults.length} SHOWN</span></div>
        <div className="assessment-list">
          {visibleResults.map((result) => {
            const site = analogSites.find((item) => item.id === result.siteId)!;
            return <button className={`assessment-card stage11-candidate ${selectedSite === site.id ? "stage11-selected" : ""}`} key={site.id} onClick={() => setSelectedSite(site.id)}>
              <div className="assessment-card-head"><div><strong>{site.name}</strong><small>{site.region}</small></div><span className="withheld-tag">{result.rank ? `RANK #${result.rank}` : "RANK WITHHELD"}</span></div>
              <div className="assessment-values">
                <div><span>SIMILARITY</span><strong>{result.score === null ? "—" : `${result.score}%`}</strong></div>
                <div><span>COVERAGE</span><strong>{result.coverage}%</strong></div>
                <div><span>CONFIDENCE</span><strong>{result.confidence === null ? "—" : `${result.confidence}%`}</strong></div>
              </div>
              <div className="completeness-track"><i style={{width:`${result.coverage}%`}}/></div>
            </button>;
          })}
        </div>
      </div>

      <div className="panel stage11-detail-panel">
        <div className="panel-header"><div><div className="panel-kicker">FEATURE BREAKDOWN</div><h2>{selectedSiteName}</h2></div><span className="step-number">DETAIL</span></div>
        {selected ? <div className="stage11-feature-list">
          {selected.featureResults.map((item) => <div className="stage11-feature-row" key={item.feature}>
            <div><strong>{featureLabels[item.feature]}</strong><small>{item.observation ? `Observed: ${item.observation.value} ${item.observation.unit}` : "No reviewed Earth observation"}</small></div>
            <div className="stage11-feature-value"><strong>{item.similarity === null ? "—" : `${item.similarity.toFixed(0)}%`}</strong><span className={item.status === "matched" ? "stage11-status-ok" : "stage11-status-missing"}>{item.status.replace(/-/g, " ")}</span></div>
          </div>)}
        </div> : <EmptyChart title="Select a candidate" detail="Choose an Earth analog to inspect its feature-level status."/>}
        <div className="model-note"><Info size={14}/><span>Feature similarity is only displayed when the corresponding source-backed measurement and target reference are compatible.</span></div>
      </div>
    </section>

    <div className="withheld-explanation"><AlertTriangle size={15}/><div><strong>Current scientific data state: no measured comparison records.</strong><span>The chart and ranking views intentionally show missing-data states. Exports contain the current registry state and do not manufacture sample values.</span></div></div>
  </div>;
}

function Metric({label,value,detail}:{label:string;value:string;detail:string}) {
  return <div className="panel metric-card"><div className="metric-top"><span className="metric-label">{label}</span></div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function EmptyChart({title,detail}:{title:string;detail:string}) {
  return <div className="stage11-empty-chart"><div className="stage11-empty-icon"><BarChart3 size={24}/></div><strong>{title}</strong><span>{detail}</span></div>;
}
