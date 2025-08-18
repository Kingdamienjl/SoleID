from __future__ import annotations

import os
import asyncio
from typing import List, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.schemas.shoe import Shoe


_vector_service_singleton: Optional["VectorService"] = None


def get_vector_service() -> "VectorService":
    global _vector_service_singleton
    if _vector_service_singleton is None:
        _vector_service_singleton = VectorService()
    return _vector_service_singleton


class VectorSearchResult:
    def __init__(self, score: float, payload: Shoe) -> None:
        self.score = score
        self.payload = payload


class VectorService:
    def __init__(self) -> None:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.collection = "shoes_v1"
        self.vector_size = 512
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            collections = self.client.get_collections()
            names = [c.name for c in collections.collections]
            if self.collection not in names:
                self.client.recreate_collection(
                    collection_name=self.collection,
                    vectors_config=qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE),
                )
        except Exception:  # noqa: BLE001
            # Best-effort creation, raise on actual usage
            pass

    async def query(self, vector: np.ndarray, top_k: int = 5) -> List[VectorSearchResult]:
        def _query() -> List[VectorSearchResult]:
            try:
                res = self.client.search(
                    collection_name=self.collection,
                    query_vector=vector.tolist(),
                    limit=top_k,
                    with_payload=True,
                    score_threshold=None,
                )
            except Exception:
                # If Qdrant unavailable, return empty results; caller handles gracefully
                return []
            results: List[VectorSearchResult] = []
            for p in res:
                payload = p.payload or {}
                shoe = Shoe(**payload)
                results.append(VectorSearchResult(score=float(p.score), payload=shoe))
            return results

        return await asyncio.to_thread(_query)

    async def upsert(self, ids: List[str], vectors: np.ndarray, payloads: List[dict]) -> None:
        def _upsert() -> None:
            points = []
            for idx, vec in enumerate(vectors):
                points.append(
                    qmodels.PointStruct(
                        id=ids[idx],
                        vector=vec.tolist(),
                        payload=payloads[idx],
                    )
                )
            self.client.upsert(collection_name=self.collection, points=points)

        await asyncio.to_thread(_upsert)
