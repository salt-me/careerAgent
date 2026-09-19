"""Read path for the batch-built 10,000+ public-JD Qdrant collection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from .bulk_vector_store import COLLECTION_NAME, DEFAULT_STORAGE
from .vector_retrieval import MODEL_NAME


@dataclass(frozen=True)
class BulkSearchHit:
    id: str
    title: str
    company: str
    position: str
    job_family: str
    location: str
    source_name: str
    source_url: str
    source_status: str
    captured_at: str
    score: float
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BulkJobSearchStore:
    def __init__(self, storage_path: str | Path = DEFAULT_STORAGE) -> None:
        self.client = QdrantClient(path=str(storage_path))
        self.embedding = TextEmbedding(model_name=MODEL_NAME)

    @staticmethod
    def _as_lists(vectors: Iterable[Any]) -> list[list[float]]:
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]

    def is_ready(self) -> bool:
        return self.client.collection_exists(COLLECTION_NAME)

    @staticmethod
    def _filter(
        *, position: str | None, source_name: str | None, open_only: bool
    ) -> models.Filter | None:
        conditions: list[models.FieldCondition] = []
        if position:
            conditions.append(models.FieldCondition(key="position", match=models.MatchValue(value=position)))
        if source_name:
            conditions.append(models.FieldCondition(key="source_name", match=models.MatchValue(value=source_name)))
        if open_only:
            conditions.append(models.FieldCondition(key="source_status", match=models.MatchValue(value="open")))
        return models.Filter(must=conditions) if conditions else None

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        position: str | None = None,
        source_name: str | None = None,
        open_only: bool = False,
    ) -> list[BulkSearchHit]:
        if not self.is_ready():
            raise RuntimeError("Scalable job vector store is not indexed. Build it with BulkJobVectorStore().rebuild().")
        vector = self._as_lists(self.embedding.embed([query]))[0]
        points = self.client.query_points(
            COLLECTION_NAME,
            query=vector,
            query_filter=self._filter(position=position, source_name=source_name, open_only=open_only),
            limit=limit,
            with_payload=True,
        ).points
        return [
            BulkSearchHit(
                id=str(point.payload["id"]),
                title=str(point.payload["title"]),
                company=str(point.payload["company"]),
                position=str(point.payload["position"]),
                job_family=str(point.payload["job_family"]),
                location=str(point.payload["location"]),
                source_name=str(point.payload["source_name"]),
                source_url=str(point.payload["source_url"]),
                source_status=str(point.payload["source_status"]),
                captured_at=str(point.payload["captured_at"]),
                score=round(float(point.score), 4),
                excerpt=str(point.payload["text"])[:300],
            )
            for point in points
        ]
