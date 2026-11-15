import { useEffect, useState } from "react";
import { Download, FileText, FileSpreadsheet, RefreshCw, AlertTriangle, ShieldCheck } from "lucide-react";
import { terrascanApi, type ScientificReportSummary } from "../services/api";

export default function ScientificReportsWorkspace() {
  const [target,setTarget]=useState<"Moon"|"Mars">("Mars");
  const [summary,setSummary]=useState<ScientificReportSummary|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const load=async(body: "Moon"|"Mars")=>{
    setLoading(true);setError("");
    try{setSummary(await terrascanApi.reportSummary(body));}
    catch(e){setError(e instanceof Error?e.message:"Unable to load report summary.");setSummary(null);}
    finally{setLoading(false);}
  };
  useEffect(()=>{void load(target);},[target]);
  const download=(kind:"pdf"|"csv")=>{
    const base=(import.meta.env.VITE_API_BASE_URL||"http://127.0.0.1:8000").replace(/\/$/,"");
    const a=document.createElement("a");a.href=`${base}/api/reports/${target}/${kind}`;
    a.download=`terrascan-${target.toLowerCase()}-evidence-report.${kind}`;
    document.body.appendChild(a);a.click();a.remove();
  };
  return <section className="scientific-reports-workspace">
    <div className="panel report-controls">
      <div><div className="panel-kicker">REPORT CONFIGURATION</div><h2>Evidence-backed scientific report</h2><p>Exports include reviewed records, source hashes and review status. No comparison score is generated.</p></div>
      <div className="report-control-actions">
        <label>Target body<select value={target} onChange={e=>setTarget(e.target.value as "Moon"|"Mars")}><option>Moon</option><option>Mars</option></select></label>
        <button className="subtle-button" onClick={()=>void load(target)} disabled={loading}><RefreshCw size={13}/> Refresh</button>
      </div>
    </div>
    {error&&<div className="report-alert"><AlertTriangle size={15}/>{error}. Confirm the FastAPI backend is running.</div>}
    <div className="report-metrics">
      <div className="panel"><span className="panel-kicker">APPROVED OBSERVATIONS</span><strong>{summary?.observations.length??"—"}</strong></div>
      <div className="panel"><span className="panel-kicker">APPROVED SOURCE MANIFESTS</span><strong>{summary?.approved_manifests.length??"—"}</strong></div>
      <div className="panel"><span className="panel-kicker">TARGET REFERENCES</span><strong>{summary?.target_references.length??"—"}</strong></div>
      <div className="panel"><span className="panel-kicker">COMPARISON STATUS</span><strong className="report-not-computed">NOT COMPUTED</strong></div>
    </div>
    <div className="panel report-export-panel">
      <div className="report-export-icon"><FileText size={22}/></div>
      <div className="report-export-copy"><h3>Generate {target} evidence report</h3><p>PDF includes a readable summary, approved observations, target references, dataset provenance, hashes and limitations. CSV provides a row-based evidence export.</p></div>
      <div className="report-export-buttons">
        <button className="report-download-button" onClick={()=>download("pdf")}><Download size={14}/> PDF report</button>
        <button className="subtle-button" onClick={()=>download("csv")}><FileSpreadsheet size={14}/> CSV data</button>
      </div>
    </div>
    <div className="panel report-integrity">
      <ShieldCheck size={17}/><div><strong>Scientific integrity rules</strong><ul>
        <li>Only observations and source manifests marked approved are included.</li>
        <li>Missing records remain missing; exports do not add example values.</li>
        <li>Target reference records are shown as stored, without inferred ranges.</li>
        <li>Similarity, candidate rankings and mission suitability are not calculated by the report service.</li>
      </ul></div>
    </div>
    {summary&&<div className="panel report-preview">
      <div className="panel-header"><div><div className="panel-kicker">LIVE REPORT PREVIEW</div><h2>{target} · Evidence inventory</h2></div><span className="report-generated">{new Date(summary.generated_at).toLocaleString()}</span></div>
      {summary.observations.length? <div className="report-table-wrap"><table><thead><tr><th>Site</th><th>Feature</th><th>Value</th><th>Unit</th><th>Quality</th><th>Source dataset</th></tr></thead><tbody>
        {summary.observations.map((r,i)=><tr key={`${String(r.id)}-${i}`}><td>{String(r.site_id)}</td><td>{String(r.criterion)}</td><td>{String(r.value)}</td><td>{String(r.unit)}</td><td>{String(r.quality)}</td><td>{String(r.dataset_id)}</td></tr>)}
      </tbody></table></div>:<div className="report-empty">No approved Earth observations are currently available for this report.</div>}
      <div className="report-footnote">{summary.interpretation}</div>
    </div>}
    {loading&&<div className="report-loading">Loading current database records…</div>}
  </section>;
}
