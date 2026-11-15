import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, XCircle, RefreshCw, ShieldCheck, AlertTriangle } from "lucide-react";
import { terrascanApi, type DatasetManifest, type ScientificObservation } from "../services/api";

type Queue = { manifests: DatasetManifest[]; observations: ScientificObservation[]; counts: { manifests: number; observations: number } };

export default function EvidenceReviewWorkspace() {
  const [queue, setQueue] = useState<Queue | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try { setError(""); setQueue(await terrascanApi.reviewQueue()); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load review queue."); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const decide = async (kind: "manifest" | "observation", id: string, decision: "approved" | "rejected") => {
    const reason = (reasons[id] || "").trim();
    if (reviewer.trim().length < 2) { setError("Enter reviewer identification before submitting a decision."); return; }
    if (reason.length < 10) { setError("A review reason of at least 10 characters is required."); return; }
    setBusy(id); setError(""); setMessage("");
    try {
      if (kind === "manifest") await terrascanApi.reviewManifest(id, decision, reason, reviewer.trim());
      else await terrascanApi.reviewObservation(id, decision, reason, reviewer.trim());
      setMessage(`${kind === "manifest" ? "Dataset manifest" : "Scientific observation"} ${decision}.`);
      setReasons(current => { const next = { ...current }; delete next[id]; return next; });
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Review action failed."); }
    finally { setBusy(null); }
  };

  const card = (kind: "manifest" | "observation", item: DatasetManifest | ScientificObservation) => {
    const id = item.id;
    const obs = item as ScientificObservation;
    const manifest = item as DatasetManifest;
    return <article className="panel evidence-review-card" key={id}>
      <div className="review-card-top">
        <div><div className="panel-kicker">{kind === "manifest" ? "SOURCE DATASET MANIFEST" : "EXTRACTED SCIENTIFIC OBSERVATION"}</div>
          <h3>{kind === "manifest" ? manifest.dataset_id : `${obs.site_id} · ${obs.criterion}`}</h3>
        </div>
        <span className="review-state">PENDING REVIEW</span>
      </div>
      {kind === "manifest" ? <>
        <div className="review-meta"><span>Version <b>{manifest.version}</b></span><span>SHA-256 <b>{manifest.sha256.slice(0, 16)}…</b></span></div>
        <p className="review-source">{manifest.source_uri}</p>
      </> : <>
        <div className="review-meta"><span>Value <b>{obs.value} {obs.unit}</b></span><span>Target <b>{obs.target_body}</b></span><span>Quality <b>{obs.quality}</b></span></div>
        <p className="review-source">Source manifest: {obs.manifest_id}</p>
      </>}
      <label className="review-label">Review rationale (required)</label>
      <textarea value={reasons[id] || ""} onChange={e => setReasons(current => ({ ...current, [id]: e.target.value }))} placeholder="Check source provenance, units, CRS, temporal coverage, uncertainty and quality..." rows={3}/>
      <div className="review-actions">
        <button className="review-reject" disabled={busy === id} onClick={() => void decide(kind,id,"rejected")}><XCircle size={14}/> Reject</button>
        <button className="review-approve" disabled={busy === id} onClick={() => void decide(kind,id,"approved")}><CheckCircle2 size={14}/> Approve</button>
      </div>
    </article>;
  };

  return <section className="evidence-review-workspace">
    <div className="panel review-controls">
      <div className="review-control-copy"><ShieldCheck size={18}/><div><strong>Human evidence quality gate</strong><span>Only approved observations are eligible for comparison-run snapshots.</span></div></div>
      <div className="review-control-actions"><input value={reviewer} onChange={e => setReviewer(e.target.value)} placeholder="Reviewer ID / initials" aria-label="Reviewer ID"/><button className="subtle-button" onClick={() => void refresh()}><RefreshCw size={13}/> Refresh queue</button></div>
    </div>
    {error && <div className="review-alert review-error"><AlertTriangle size={15}/>{error}</div>}
    {message && <div className="review-alert review-success"><CheckCircle2 size={15}/>{message}</div>}
    <div className="review-summary">
      <div className="panel"><span className="panel-kicker">PENDING MANIFESTS</span><strong>{queue?.counts.manifests ?? "—"}</strong></div>
      <div className="panel"><span className="panel-kicker">PENDING OBSERVATIONS</span><strong>{queue?.counts.observations ?? "—"}</strong></div>
      <div className="panel"><span className="panel-kicker">REVIEW POLICY</span><strong>Human decision</strong></div>
    </div>
    <div className="review-section-heading"><div><div className="panel-kicker">STAGE 1</div><h2>Dataset source manifests</h2><p>Verify source identity and product metadata before allowing evidence registration.</p></div></div>
    <div className="review-card-grid">{queue?.manifests.length ? queue.manifests.map(item => card("manifest",item)) : <div className="review-empty">No pending dataset manifests.</div>}</div>
    <div className="review-section-heading"><div><div className="panel-kicker">STAGE 2</div><h2>Scientific observations</h2><p>Approve individual measurements only after their source manifest has been approved.</p></div></div>
    <div className="review-card-grid">{queue?.observations.length ? queue.observations.map(item => card("observation",item)) : <div className="review-empty">No pending scientific observations.</div>}</div>
    <p className="review-footnote">Approval is a workflow decision, not independent scientific validation. Confirm official product labels, units, CRS/datum, temporal coverage, uncertainty and processing methodology before approving.</p>
  </section>;
}
