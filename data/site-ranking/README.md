# Mission-site ranking input workspace

No site records or ranking results are supplied. Build a JSON input with schema `terrascan.site-ranking-input.v1`:

- `targetBody`: `Moon` or `Mars`
- `policy`: explicit non-negative `analogWeight` and `uncertaintyPenaltyWeight`, at least one positive
- `sites`: unique `siteId`, `siteName`, path to a Stage 25 analog report, path to a Stage 17 suitability assessment snapshot, and explicit `uncertaintyFraction` from 0 to 1 with an independently documented basis.

The site ID must match a ranked candidate ID in the analog report and the site ID in the suitability assessment. Suitability must be `eligible` and its snapshot must contain approved evidence. All other sites are withheld rather than assigned a rank.

Run:
`python scripts/terrascan_rank_sites.py path/to/ranking-input.json --output data/site-ranking/review-001.json`

The ranking utility is a transparent policy-weighted decision-support score, not a probability or mission safety score. Review all policy weights, source evidence and uncertainty basis before interpretation. No ranking is automatically approved.
