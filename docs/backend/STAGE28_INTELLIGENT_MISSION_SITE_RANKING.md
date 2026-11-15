# Stage 28 — Intelligent Mission-Site Ranking

## Scope
Combines Stage 25 approved-feature analog discovery results with Stage 17 mission-constraint assessment snapshots to create an explainable, evidence-gated shortlist. It does not retrain a model or create a landing-site recommendation.

## Input and execution
See `data/site-ranking/README.md` for the exact input schema. Execute:
```bash
python scripts/terrascan_rank_sites.py path/to/ranking-input.json --output data/site-ranking/review-001.json
python -m unittest scripts.test_terrascan_rank_sites -v
```
Existing report files are never overwritten.

## Gate logic
A site is ranked only when:
- Exactly one ranked Stage 25 analog result exists for its site ID and has a finite score in [0, 100].
- Stage 25 report disposition and evidence-approval state match the expected contract.
- Stage 17 suitability assessment matches the site ID, target body is Moon or Mars, and status is `eligible`.
- The assessment input snapshot matches the site ID and contains at least one approved-evidence record.
- Operator-supplied uncertainty fraction is explicit and within [0, 1].

Failed or incomplete gates are listed under `withheldSites` with reasons. They are never assigned a rank.

## Ranking formula
`(analogWeight * analogSimilarityScore + uncertaintyPenaltyWeight * 100 * (1 - uncertaintyFraction)) / (analogWeight + uncertaintyPenaltyWeight)`

Weights are operator-supplied and normalized by their sum. Ties are broken by ascending site ID. The uncertainty fraction is an operator-provided penalty input, not a calibrated model output or independently estimated confidence interval.

## Safeguards and limitations
- No evidence is automatically approved; the engine does not alter source review states.
- Suitability `eligible` is a constraint-gate result, not a landing-safety certification or authorization.
- Analog similarity is not probability, geological equivalence or mission suitability.
- The composite utility is policy-dependent and not an objective scientific truth.
- SHA-256 binds the current report files but does not independently verify the underlying science.
- No site selection, mission readiness determination or operational authorization is performed.
- No real candidate data or rankings are bundled.
