from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
import time
import logging
from starlette_exporter import PrometheusMiddleware, handle_metrics

from app.routes.match import router as match_router
from app.routes.prices import router as prices_router
from app.services.vector import get_vector_service

app = FastAPI(title="SoleID Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("soleid")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def timing_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info("path=%s status=%s duration_ms=%s", request.url.path, response.status_code, duration_ms)
    return response

app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(match_router, prefix="")
app.include_router(prices_router, prefix="")
app.include_router(match_router, prefix="/api")
app.include_router(prices_router, prefix="/api")

@app.get("/api/stats")
def stats() -> dict:
    try:
        vs = get_vector_service()
        collections = vs.client.get_collections()
        count = len(collections.collections)
        return {"qdrantCollections": count, "vectorSize": vs.vector_size}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Vector service unavailable: {exc}") from exc

@app.get("/ready")
def ready() -> dict:
    try:
        vs = get_vector_service()
        _ = vs.client.get_collections()
        return {"status": "ready"}
    except Exception:
        return {"status": "degraded"}
