# Stage 10 — Earth–Moon–Mars Analog Comparison Engine

## Delivered

- Added a typed feature-comparison engine for slope distribution, surface roughness, thermal environment, elevation range and geological class.
- Added per-feature statuses for missing observation, missing target reference, unit mismatch and invalid values.
- Numeric feature scores use a bounded range-distance function; categorical geology uses exact category agreement.
- Aggregate similarity and rank are withheld until all configured feature pairs are present and compatible.
- Coverage is reported independently of similarity. Confidence is a quality-based heuristic and is not a probability.
- Added a dedicated Analog Comparison workspace to the React navigation.

## Data and scoring policy

The current observation and target-feature arrays are intentionally empty. The UI therefore displays candidates with zero coverage and no rankings. The approximate candidate map coordinates are not used as measurements.

Initial feature weights (slope 25%, roughness 20%, thermal 25%, elevation range 15%, geology 15%) are provisional research assumptions. They must be reviewed before operational use.

No automatic conversion is performed between incompatible physical units or planetary coordinate systems. A future extension may add explicit, audited unit conversions and feature-specific uncertainty propagation.

## Limitations

- No real Earth, lunar or Martian feature measurements have been populated.
- No site ranking is currently scientifically supportable.
- A feature-level ranking does not imply mission suitability.
- Full frontend build should be run in a Node environment with dependencies installed.
