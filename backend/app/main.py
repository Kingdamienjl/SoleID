from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.match import router as match_router
from app.routes.prices import router as prices_router

app = FastAPI(title="SoleID Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(match_router, prefix="")
app.include_router(prices_router, prefix="")
