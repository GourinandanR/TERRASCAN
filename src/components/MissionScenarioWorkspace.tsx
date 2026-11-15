import { useState } from "react";

const API = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const example = JSON.stringify({
  name: "Unvalidated surface operations scenario",
  target_body: "Mars",
  site_id: "user-defined-site-id",
  activities: [
    { id: "A", name: "Site reconnaissance", duration_hours: 12, depends_on: [], resources: { power_kwh: 8 } },
    { id: "B", name: "Deploy surface instruments", duration_hours: 6, depends_on: ["A"], resources: { power_kwh: 15 } },
    { id: "C", name: "Begin science operations", duration_hours: 24, depends_on: ["B"], resources: { power_kwh: 20 } }
  ],
  resource_limits: { power_kwh: 25 }
}, null, 2);

export default function MissionScenarioWorkspace() {
  const [payload, setPayload] = useState(example);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true); setError(""); setResult(null);
    try {
      const response = await fetch(`${API}/api/mission-scenarios`, { method: "POST", headers: { "Content-Type": "application/json" }, body: payload });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Scenario could not be created");
      setResult(data);
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
    finally { setBusy(false); }
  }
  return <div className="workspace-stack">
    <section className="panel workspace-panel">
      <div className="panel-header"><div><div className="panel-kicker">STAGE 18 · SCENARIO DESIGN</div><h2>Mission scenario configuration</h2></div><span className="status-tag">HYPOTHETICAL INPUTS</span></div>
      <p>Define activity durations, dependency links and resource demand. The planner calculates an earliest-start schedule; it does not predict real mission performance.</p>
      <textarea aria-label="Mission scenario JSON" value={payload} onChange={e => setPayload(e.target.value)} rows={18} style={{ width: "100%", fontFamily: "monospace", fontSize: 12, padding: 14, borderRadius: 8, background: "var(--surface-2, #101923)", color: "inherit", border: "1px solid var(--border, #334155)" }} />
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 14 }}><button className="primary-button" onClick={run} disabled={busy}>{busy ? "Planning…" : "Create scenario"}</button><span className="muted-icon">Inputs are saved as an immutable snapshot.</span></div>
      {error && <p role="alert" style={{ color: "#dc7777" }}>{error}</p>}
    </section>
    {result && <section className="panel workspace-panel">
      <div className="panel-header"><div><div className="panel-kicker">SAVED SCENARIO · {result.id.slice(0, 8)}</div><h2>{result.name}</h2></div><span className="status-tag">{result.status.toUpperCase()}</span></div>
      <div className="metric-grid"><div className="metric-card"><div className="metric-label">PLANNED DURATION</div><div className="metric-value">{result.result.duration_hours} h</div></div><div className="metric-card"><div className="metric-label">ACTIVITIES</div><div className="metric-value">{result.result.schedule.length}</div></div><div className="metric-card"><div className="metric-label">SUITABILITY GATE</div><div className="metric-value" style={{ fontSize: 17 }}>{result.result.suitability_gate}</div></div></div>
      <div style={{ overflowX: "auto", marginTop: 18 }}><table className="data-table"><thead><tr><th>Activity</th><th>Start (h)</th><th>Finish (h)</th><th>Dependencies</th></tr></thead><tbody>{result.result.schedule.map((a: any) => <tr key={a.activity_id}><td>{a.name}</td><td>{a.start_hour}</td><td>{a.finish_hour}</td><td>{a.depends_on.join(", ") || "—"}</td></tr>)}</tbody></table></div>
      {result.result.resource_issues.length > 0 && <p>Resource issues: {JSON.stringify(result.result.resource_issues)}</p>}
      <p className="muted-icon">Operational authorization: not assessed. This schedule is not a mission approval.</p>
    </section>}
  </div>;
}
