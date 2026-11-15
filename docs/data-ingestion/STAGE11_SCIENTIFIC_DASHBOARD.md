# Stage 11 — Interactive Scientific Comparison Dashboard

## Delivered
- Interactive target selector (Moon/Mars), candidate selector and ranking-status filter.
- Similarity ranking chart using Recharts. It shows a clear unavailable state when no candidate has a complete, compatible feature profile.
- Feature coverage chart distinguishing matched and missing candidates.
- Candidate comparison list with rank, similarity, coverage and confidence fields.
- Feature-by-feature detail panel for the selected candidate.
- CSV and JSON export of the current comparison state, feature statuses, model weights and generation timestamp.
- Responsive dashboard layout and explicit missing-data messaging.

## Data integrity
The Stage 10 observation and target reference registries remain empty. Consequently:
- Similarity ranking chart is intentionally empty.
- Feature coverage chart shows all candidates as missing for each feature.
- No ranking, similarity score or confidence value is fabricated.
- Exported reports preserve null values and missing statuses.

## Technical notes
- Recharts is already part of the frontend dependency set.
- Export uses browser Blob downloads and does not send data to a server.
- The dashboard reads the same Stage 10 comparison engine; no second scoring implementation was introduced.
- Full application build requires `npm install` followed by `npm run typecheck` and `npm run build`.
