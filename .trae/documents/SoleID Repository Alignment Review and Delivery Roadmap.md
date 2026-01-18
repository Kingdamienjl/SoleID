## Note on Skills
No external skill is relevant; this requires repository-wide planning and code changes, not skill creation.

## Strategic Analysis
### Discrepancy Patterns
- Dual backends: FastAPI under backend/app vs Flask under sneaker-scraper with overlapping endpoints.
- Android base URL couples to "/api" and expects Flask-style endpoints, while FastAPI serves at root.
- README and docs describe a structure that doesn’t match actual files; placeholder usernames persist.
- Requirements inconsistencies: sneaker-scraper lists FastAPI but uses Flask.
- Security defaults in Android build.gradle include weak fallback keystore passwords.

### Systemic Issues & Root Causes
- Parallel prototypes merged into one repo without consolidation.
- Documentation drift from rapid iteration and mixed stacks.
- Missing API contract owned source-of-truth; client/server evolved independently.
- Convenience build defaults introduce security risks for local developer experience.

### Long-Term Prevention Strategies
- Define single backend of record (FastAPI) and deprecate overlapping Flask HTTP responsibilities.
- Enforce API contract via shared OpenAPI schema and generated client models.
- Establish doc ownership rules with CI link checks and structure validation.
- Harden secrets handling: no defaults, mandatory env-based configuration, pre-commit secret scanning.

### Process Improvements
- Introduce CI pipelines for tests, lint, secret scans, and doc consistency.
- Require architectural review for adding new endpoints.
- Maintain CHANGELOG with impact and risk notes; use ADRs for major decisions.

## Phase 1 Implementation (Simultaneous)
### Critical Security Fixes
- Remove insecure fallback keystore credentials; fail build if properties missing. See [app/build.gradle](file:///d:/Projects/SoleID/android-app/app/build.gradle#L49-L80).
- Confirm secrets confinement: keep google-services.json, keystores, and local.properties ignored per [.gitignore](file:///d:/Projects/SoleID/.gitignore#L61-L75); add pre-commit secret scan.
- Add OkHttp auth/header interceptor and token manager; centralize authorization in [NetworkModule.kt](file:///d:/Projects/SoleID/android-app/app/src/main/java/com/soleid/app/di/NetworkModule.kt).

### High-Impact Functionality Issues
- Align Android networking with FastAPI: implement DTOs for [MatchResponse](file:///d:/Projects/SoleID/backend/app/schemas/match.py) and [PriceSnapshot](file:///d:/Projects/SoleID/backend/app/schemas/price.py); add client calls for POST /match and GET /prices.
- Add FastAPI "/api" router prefix to maintain backward compatibility with current Android base URL; expose /api/health, /api/match, /api/prices. See [main.py](file:///d:/Projects/SoleID/backend/app/main.py).
- Implement /api/stats on FastAPI to replace Flask stats, returning minimal service metrics.

### Immediate Stability Improvements
- Strengthen error mapping and retries on Android; unify network error handling paths (timeouts, HTTP codes). See [NetworkErrorHandler.kt](file:///d:/Projects/SoleID/android-app/app/src/main/java/com/soleid/app/utils/NetworkErrorHandler.kt).
- Maintain graceful degradation when Qdrant is unavailable (already present in [vector.py](file:///d:/Projects/SoleID/backend/app/services/vector.py#L61-L69)); add health readiness checks.

### Documentation of Changes
- Update README to reflect actual structure and single backend of record; remove placeholders. See [README.md](file:///d:/Projects/SoleID/README.md).
- Update [ANDROID.md](file:///d:/Projects/SoleID/docs/ANDROID.md) to describe BuildConfig-driven base URL, not local.properties.
- Maintain a CHANGELOG.md and a Phase 1 report with risk, impact, tests, and deployment verification.

## Phase 2 Implementation (Simultaneous)
### Architectural Enhancements
- Consolidate Flask endpoints into FastAPI (health/stats/catalog as needed) and gate sneaker-scraper to ingestion-only use.
- Standardize embedding service configuration and introduce environment-based toggles for MOCK_EMBEDDING. See [embedding.py](file:///d:/Projects/SoleID/backend/app/services/embedding.py).

### Performance Optimizations
- Add Redis caching for price snapshots (already optional in [requirements](file:///d:/Projects/SoleID/backend/requirements.txt#L21-L22)); wire cache in FastAPI services.
- Introduce Android Macrobenchmark module for startup/search/detail flows; enable LeakCanary and StrictMode in debug.
- Add OkHttp event listener for timing and improve DNS/cache tuning.
- Validate Qdrant collection setup and tune distance/limits per use case. See [vector.py](file:///d:/Projects/SoleID/backend/app/services/vector.py#L43-L51).

### Scalability Improvements
- Formalize Docker images and compose stack; document env contracts. See [docker-compose.yml](file:///d:/Projects/SoleID/ops/docker-compose.yml).
- Parameterize worker counts (uvicorn workers per CPU) and enable horizontal scaling behind a reverse proxy.

### Monitoring Mechanisms
- Add backend request logging and metrics endpoints (/metrics or middleware); log match timings and cache hits.
- Add Android analytics toggled by build flags; track network errors and response times.

## Documentation Artifacts (Both Phases)
- Change logs: CHANGELOG.md with entries per fix/enhancement.
- Risk assessments: per change, covering impact on security and availability.
- Impact analysis: functional coverage, user flows affected, performance deltas.
- Testing results: unit/integration summaries; Python [run_tests.sh](file:///d:/Projects/SoleID/run_tests.sh), Android unit tests.
- Deployment verification: steps and checks for Docker stack and mobile client base URL alignment.

## Implementation Checklist (Files/Modules)
- Android
  - Network: add auth interceptor + token manager in [NetworkModule.kt](file:///d:/Projects/SoleID/android-app/app/src/main/java/com/soleid/app/di/NetworkModule.kt).
  - API client: extend [SoleIDApiService.kt](file:///d:/Projects/SoleID/android-app/app/src/main/java/com/soleid/app/data/api/SoleIDApiService.kt) with /match and /prices; remove unused endpoints conflicting with FastAPI.
  - Build: harden [app/build.gradle](file:///d:/Projects/SoleID/android-app/app/build.gradle) to fail without keystore properties; retain secret confinement.
  - Stability: ensure [SettingsScreen.kt](file:///d:/Projects/SoleID/android-app/app/src/main/java/com/soleid/app/presentation/settings/SettingsScreen.kt) and navigation remain consistent.
- Backend (FastAPI)
  - Routes: add /api prefix, implement /api/stats; keep [/match](file:///d:/Projects/SoleID/backend/app/routes/match.py) and [/prices](file:///d:/Projects/SoleID/backend/app/routes/prices.py).
  - Services: wire optional Redis cache; confirm Qdrant setup in [vector.py](file:///d:/Projects/SoleID/backend/app/services/vector.py).
  - Ops: validate [docker-compose.yml](file:///d:/Projects/SoleID/ops/docker-compose.yml) and [Makefile](file:///d:/Projects/SoleID/ops/Makefile) targets.
- Docs
  - Update [README.md](file:///d:/Projects/SoleID/README.md), [ANDROID.md](file:///d:/Projects/SoleID/docs/ANDROID.md), [API.md](file:///d:/Projects/SoleID/docs/API.md), and add CHANGELOG.md.

## Risks & Mitigations
- Contract drift: mitigate via shared OpenAPI and CI checks.
- Qdrant downtime: degrade gracefully; pre-flight health checks.
- Performance variance (CPU embedding): add caching and consider GPU in prod.
- Secret handling errors: build fail-fast and pre-commit secret scanning.

## Verification Plan
- Git parity: verify branch/commit status (`master` aligned with `origin/master`).
- Backend: run compose; hit /api/health, /api/match, /api/prices; confirm responses.
- Android: build debug; validate base URL and endpoints; test match and price flows.
- Tests: execute Python tests via [run_tests.sh](file:///d:/Projects/SoleID/run_tests.sh); run Android unit tests; collect metrics.

## Deliverables (This Engagement)
- Implemented Phase 1 and Phase 2 changes as above.
- Updated documentation: CHANGELOG, risk/impact/testing/deployment verification reports.
- Consolidated backend with clear API contract and monitoring hooks.

Please confirm; once approved, I will execute the changes, validate with tests, and deliver the documentation artifacts.