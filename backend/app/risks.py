"""Qualitative, non-probabilistic mission risk and uncertainty classification."""
from __future__ import annotations

LIKELIHOODS={"rare","unlikely","possible","likely","unknown"}
IMPACTS={"negligible","minor","moderate","major","severe","unknown"}
UNCERTAINTIES={"measured","estimated","inferred","unknown"}

def assess_risks(items: list[dict]) -> dict:
    results=[]
    for item in items:
        likelihood=item["likelihood"]; impact=item["impact"]; uncertainty=item["uncertainty"]
        if likelihood not in LIKELIHOODS or impact not in IMPACTS or uncertainty not in UNCERTAINTIES:
            raise ValueError("unsupported qualitative category")
        if likelihood=="unknown" or impact=="unknown" or uncertainty=="unknown":
            state="indeterminate"
            rationale="Likelihood, impact, or evidence uncertainty is unknown; no numeric probability is inferred."
        elif impact in {"major","severe"} and likelihood in {"possible","likely"}:
            state="attention-required"
            rationale="Qualitative likelihood and impact indicate a risk requiring documented mitigation."
        else:
            state="monitor"
            rationale="Qualitative classification only; this is not a probability or safety certification."
        results.append({"risk_id":item["risk_id"],"state":state,"rationale":rationale,
                        "mitigation_state":"documented" if item["mitigation"].strip() else "not-documented",
                        "evidence_state":"referenced" if item["evidence_refs"] else "not-referenced"})
    return {"items":results,
            "overall_state":"indeterminate" if any(x["state"]=="indeterminate" for x in results) else
                           ("attention-required" if any(x["state"]=="attention-required" for x in results) else "monitor"),
            "method":"Qualitative categories only. No numeric likelihood, probability, expected loss, composite risk score, or risk ranking is calculated."}
