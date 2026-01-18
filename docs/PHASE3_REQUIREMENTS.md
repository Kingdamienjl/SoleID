# Phase 3 Requirements and Progress

## Objectives
- Consolidate backend APIs under FastAPI with shared OpenAPI schema.
- Generate Android client models from OpenAPI to prevent drift.
- Integrate crash reporting (Crashlytics or Sentry) behind feature flags.
- Add CI pipelines (backend pytest, Android unit, secret scans, doc checks).
- Implement Android Macrobenchmark module for startup/search/detail flows.
- Harden data ingestion; finalize Qdrant indexing and payload schemas.

## Deliverables
- OpenAPI definition published from FastAPI.
- Android client generation pipeline (Gradle task).
- CI workflows in GitHub Actions for tests and checks.
- Macrobenchmark module with baseline metrics.
- Documentation updates reflecting contracts and observability.

## Progress Tracking
- [ ] OpenAPI contract exported and versioned
- [ ] Android client generation integrated
- [ ] Crash telemetry initialized with build flags
- [ ] CI workflows merged and green
- [ ] Macrobenchmark results recorded
- [ ] Qdrant schema validation completed

## Risks and Mitigations
- Tooling complexity: phase tasks in small PRs; use templates.
- CI flakiness: cache dependencies, pin versions.
- API change management: ADRs and versioned schema.

