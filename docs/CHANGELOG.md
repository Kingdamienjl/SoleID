# Changelog

## 2026-01-18
- Android: Enforced secure signing; removed insecure keystore defaults.
- Android: Added TokenManager and OkHttp AuthInterceptor.
- Android: Added OkHttp NetworkEventListener for timing.
- Android: Enabled StrictMode in debug and added LeakCanary.
- Backend: Added /api-prefixed routers and /api/stats endpoint.
- Backend: Added /ready endpoint for Qdrant connectivity check.
- Backend: Added HTTP timing middleware for request metrics.
- Ops: Added Redis service to docker-compose; configured REDIS_URL.
- Docs: Updated ANDROID.md networking note; fixed GitHub links in README.

