#!/usr/bin/env python3
"""Evidence-gated multi-criteria mission-site ranking.

Consumes Stage 25 analog discovery reports and Stage 17 suitability assessment
snapshots. It is a transparent decision-support shortlist, not authorization.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, sys
from datetime import datetime, timezone
from pathlib import Path
HASH=re.compile(r"^[0-9a-f]{64}$")

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def read(path):
    p=Path(path).resolve()
    if not p.is_file(): raise ValueError(f"Required input file not found: {p}")
    return json.loads(p.read_text(encoding="utf-8")),p

def run(payload,payload_path):
    if payload.get("schemaVersion")!="terrascan.site-ranking-input.v1":
        raise ValueError("schemaVersion must be terrascan.site-ranking-input.v1")
    policy=payload.get("policy") or {}
    aw=policy.get("analogWeight"); upw=policy.get("uncertaintyPenaltyWeight")
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in (aw,upw)) or aw+upw<=0:
        raise ValueError("policy requires finite non-negative analogWeight and uncertaintyPenaltyWeight with positive sum")
    sites=payload.get("sites")
    if not isinstance(sites,list) or not sites: raise ValueError("sites must be a non-empty list")
    seen=set(); ranked=[]; withheld=[]
    for item in sites:
        sid=item.get("siteId")
        if not isinstance(sid,str) or not sid.strip() or sid in seen: raise ValueError("Every site requires a unique non-empty siteId")
        seen.add(sid)
        name=item.get("siteName")
        if not isinstance(name,str) or not name.strip(): raise ValueError(f"{sid}: siteName required")
        analog_path=Path(item.get("analogReport","")).resolve()
        suitability_path=Path(item.get("suitabilitySnapshot","")).resolve()
        analog,ap=read(analog_path); suit,sp=read(suitability_path)
        reasons=[]
        if analog.get("scientificDisposition")!="exploratory-ranking-pending-human-review":
            reasons.append("analog-report-disposition-not-recognized")
        if analog.get("evidenceApproval")!="unchanged": reasons.append("analog-report-evidence-approval-state-unrecognized")
        matches=[x for x in analog.get("results",[]) if x.get("id")==sid and x.get("status")=="ranked"]
        if len(matches)!=1: reasons.append("no-unique-ranked-analog-result-for-site")
        else:
            score=matches[0].get("similarityScore")
            if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=100:
                reasons.append("analog-score-invalid")
        if suit.get("site_id")!=sid: reasons.append("suitability-site-id-mismatch")
        if suit.get("status")!="eligible": reasons.append("mission-constraints-not-eligible")
        if suit.get("target_body") not in ("Moon","Mars","moon","mars"): reasons.append("unsupported-target-body")
        snap=suit.get("input_snapshot") or {}
        if snap.get("site_id")!=sid: reasons.append("suitability-snapshot-site-mismatch")
        evidence=snap.get("approved_evidence")
        if not isinstance(evidence,list) or not evidence: reasons.append("no-approved-evidence-recorded-in-suitability-snapshot")
        if not isinstance(item.get("uncertaintyFraction"),(int,float)) or isinstance(item.get("uncertaintyFraction"),bool) or not math.isfinite(item["uncertaintyFraction"]) or not 0<=item["uncertaintyFraction"]<=1:
            reasons.append("uncertaintyFraction-must-be-explicit-between-0-and-1")
        if reasons:
            withheld.append({"siteId":sid,"siteName":name,"status":"withheld","reasons":reasons,
              "analogReportSha256":sha(ap),"suitabilitySnapshotSha256":sha(sp)})
            continue
        analog_score=float(matches[0]["similarityScore"])
        uncertainty=float(item["uncertaintyFraction"])
        total=aw+upw
        # Weighted normalized utility. Uncertainty is a transparent penalty, not a statistical CI.
        utility=(aw*analog_score + upw*(100*(1-uncertainty)))/total
        ranked.append({"siteId":sid,"siteName":name,"status":"ranked-pending-human-review",
          "targetBody":suit["target_body"],"analogSimilarityScore":round(analog_score,4),
          "uncertaintyFraction":uncertainty,"uncertaintyPenaltyPoints":round(100*uncertainty,4),
          "rankingUtility":round(utility,4),"suitabilityStatus":suit["status"],
          "suitabilityAssessmentId":suit.get("id"),"analogReportSha256":sha(ap),
          "suitabilitySnapshotSha256":sha(sp),
          "explanation":{"analogWeight":aw,"uncertaintyPenaltyWeight":upw,
             "formula":"(analogWeight * analogSimilarityScore + uncertaintyPenaltyWeight * 100 * (1 - uncertaintyFraction)) / (analogWeight + uncertaintyPenaltyWeight)",
             "note":"Uncertainty fraction is operator-supplied and must have a documented basis; it is not inferred or calibrated by this engine."}})
    ranked.sort(key=lambda x:(-x["rankingUtility"],x["siteId"]))
    for i,x in enumerate(ranked,1): x["rank"]=i
    return {"schemaVersion":"terrascan.site-ranking-report.v1","generatedAt":datetime.now(timezone.utc).isoformat(),
      "input":str(Path(payload_path).resolve()),"inputSha256":sha(Path(payload_path)),
      "targetBody":payload.get("targetBody"),"policy":{"analogWeight":aw,"uncertaintyPenaltyWeight":upw,
      "weightsNormalized":True,"tieBreak":"siteId ascending"},
      "rankedCount":len(ranked),"withheldCount":len(withheld),"rankedSites":ranked,"withheldSites":withheld,
      "disposition":"decision-support-shortlist-pending-human-review","evidenceApproval":"unchanged",
      "missionAuthorization":"not-assessed",
      "limitations":["A similarity score is not a probability, geological equivalence or mission-suitability score.",
      "Suitability eligibility is a constraint-gate result based on user-configured thresholds; it is not a safety certification.",
      "The uncertainty fraction is user-supplied and is not independently estimated or calibrated here.",
      "The weighted utility is policy-dependent and must be reviewed before use; it is not an objective scientific truth.",
      "SHA-256 values bind the reports to their current files but do not independently validate the underlying source observations.",
      "Only approved evidence represented in the suitability snapshot is required; this tool does not re-review source records.",
      "No site is selected, recommended for landing, or operationally authorized by this report."]}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("input"); p.add_argument("--output",required=True)
    a=p.parse_args()
    try:
        data,path=read(Path(a.input)); report=run(data,path); out=Path(a.output).resolve()
        if out.exists(): raise ValueError("Refusing to overwrite existing report")
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":report["disposition"],"ranked":report["rankedCount"],"withheld":report["withheldCount"],"output":str(out)},indent=2))
    except Exception as e: print(f"TERRASCAN ranking error: {e}",file=sys.stderr); return 2
    return 0
if __name__=="__main__": raise SystemExit(main())
