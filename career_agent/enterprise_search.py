"""Semantic search over the enterprise-official augmented vector collection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from .enterprise_vector_store import COLLECTION_NAME, DEFAULT_STORAGE
from .multilingual_all_job_vector_store import MODEL_NAME


@dataclass(frozen=True)
class EnterpriseSearchHit:
    id: str
    title: str
    company: str
    position: str
    location: str
    source_name: str
    source_url: str
    source_status: str
    captured_at: str
    score: float
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EnterpriseJobSearchStore:
    def __init__(self, storage_path: str | Path = DEFAULT_STORAGE) -> None:
        self.client = QdrantClient(path=str(storage_path))
        self.embedding = TextEmbedding(model_name=MODEL_NAME)

    @staticmethod
    def _as_lists(vectors: Iterable[Any]) -> list[list[float]]:
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]

    def is_ready(self) -> bool:
        return self.client.collection_exists(COLLECTION_NAME)

    def search(
        self, query: str, *, limit: int = 10, position: str | None = None, source_name: str | None = None
    ) -> list[EnterpriseSearchHit]:
        if not self.is_ready():
            raise RuntimeError("Enterprise official vector store is not indexed. Run EnterpriseJobVectorStore().rebuild().")
        conditions: list[models.FieldCondition] = []
        if position:
            conditions.append(models.FieldCondition(key="position", match=models.MatchValue(value=position)))
        if source_name:
            conditions.append(models.FieldCondition(key="source_name", match=models.MatchValue(value=source_name)))
        vector = self._as_lists(self.embedding.embed([query]))[0]
        points = self.client.query_points(
            COLLECTION_NAME,
            query=vector,
            query_filter=models.Filter(must=conditions) if conditions else None,
            limit=limit,
            with_payload=True,
        ).points
        return [
            EnterpriseSearchHit(
                id=str(point.payload["id"]),
                title=str(point.payload["title"]),
                company=str(point.payload["company"]),
                position=str(point.payload["position"]),
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

