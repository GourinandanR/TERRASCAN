# Stage 18 — Mission Planning & Scenario Simulation

## Scope
Stage 18 adds an explicitly hypothetical scenario planner. Users provide activities, durations in hours, dependency IDs, resource demand quantities and resource capacity limits. The backend computes a deterministic earliest-start schedule over a directed acyclic dependency graph.

## API
- `POST /api/mission-scenarios` — validate and save a scenario snapshot.
- `GET /api/mission-scenarios` — list saved scenarios.
- `GET /api/mission-scenarios/{id}` — retrieve the immutable input and result snapshots.

## Scheduling semantics
An activity starts at the maximum finish time of its dependencies, or hour zero when it has none. Its finish is start plus its user-supplied duration. The schedule is a dependency-only critical-path style plan; it does not perform resource leveling, concurrency optimization, thermal/power simulation, trajectory analysis, or probabilistic risk modeling. Resource demand is checked per activity against the configured per-activity capacity. This is not a cumulative inventory or simultaneous-load model.

Cycles, self-dependencies, duplicate IDs, and unknown dependency references are rejected. Resource quantities and limits must be finite and non-negative. Unconfigured resource limits are reported as unknown; exceeded limits are reported as resource constrained.

## Suitability linkage
An optional Stage 17 suitability assessment can be attached. Its site and target body must match the scenario. A non-eligible or absent assessment is surfaced as a gate state; the scenario planner does not override it. `operational_authorization` remains `not-assessed` in all cases.

## Scientific and operational limitations
All activity names, durations, dependencies, resource units and limits are user inputs. TERRASCAN does not supply mission-validated values. The example JSON in the UI is illustrative only and must be replaced with mission-approved engineering inputs before operational use. No launch window, landing safety, crew survival, power system, consumables, communications, mobility or mission success prediction is made. Resource quantities are dimensionless labels unless the user defines and documents units in the resource key. This stage is a planning aid, not mission authorization.

## Reproducibility
Each created scenario stores the exact submitted activity list, limits, optional suitability assessment ID and suitability status at creation, plus the computed schedule. Existing scenarios are read-only; create a new scenario to revise assumptions. Audit events record scenario creation.
