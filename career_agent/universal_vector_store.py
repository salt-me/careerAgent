"""Qdrant + FastEmbed retrieval for the cross-job-family corpus."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from .universal_corpus import load_universal_records
from .vector_retrieval import MODEL_NAME


COLLECTION_NAME = "career_agent_universal_records"
DEFAULT_STORAGE = Path(__file__).resolve().parents[1] / "qdrant_storage" / "career_agent_universal"


@dataclass(frozen=True)
class UniversalRetrievalHit:
    id: str
    title: str
    company: str
    position: str
    job_family: str
    location: str
    artifact_type: str
    source_type: str
    live_vacancy: bool
    source: str
    captured_at: str
    excerpt: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UniversalVectorStore:
    def __init__(self, storage_path: str | Path = DEFAULT_STORAGE) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(self.storage_path))
        self.embedding = TextEmbedding(model_name=MODEL_NAME)

    @staticmethod
    def _as_lists(vectors: Iterable[Any]) -> list[list[float]]:
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]

    def rebuild(self) -> dict[str, str | int]:
        records = load_universal_records()
        vectors = self._as_lists(self.embedding.embed([record["text"] for record in records]))
        if self.client.collection_exists(COLLECTION_NAME):
            self.client.delete_collection(COLLECTION_NAME)
        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
        )
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[models.PointStruct(id=index, vector=vector, payload=record) for index, (record, vector) in enumerate(zip(records, vectors, strict=True))],
            wait=True,
        )
        return {
            "collection": COLLECTION_NAME,
            "documents": len(records),
            "model": MODEL_NAME,
            "storage": str(self.storage_path),
        }

    def is_ready(self) -> bool:
        return self.client.collection_exists(COLLECTION_NAME)

    @staticmethod
    def _filter(
        *, job_family: str | None, artifact_type: str | None, actionable_only: bool
    ) -> models.Filter | None:
        conditions: list[models.FieldCondition] = []
        if job_family:
            conditions.append(models.FieldCondition(key="job_family", match=models.MatchValue(value=job_family)))
        if artifact_type:
            conditions.append(models.FieldCondition(key="artifact_type", match=models.MatchValue(value=artifact_type)))
        if actionable_only:
            conditions.append(models.FieldCondition(key="live_vacancy", match=models.MatchValue(value=True)))
        return models.Filter(must=conditions) if conditions else None

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        job_family: str | None = None,
        artifact_type: str | None = None,
        actionable_only: bool = False,
    ) -> list[UniversalRetrievalHit]:
        if not self.is_ready():
            raise RuntimeError("Universal vector store is not indexed. Run `python -m career_agent.universal_cli index` first.")
        vector = self._as_lists(self.embedding.embed([query]))[0]
        points = self.client.query_points(
            COLLECTION_NAME,
            query=vector,
            query_filter=self._filter(job_family=job_family, artifact_type=artifact_type, actionable_only=actionable_only),
            limit=limit,
            with_payload=True,
        ).points
        return [
            UniversalRetrievalHit(
                id=str(point.payload["id"]),
                title=str(point.payload["title"]),
                company=str(point.payload["company"]),
                position=str(point.payload["position"]),
                job_family=str(point.payload["job_family"]),
                location=str(point.payload["location"]),
                artifact_type=str(point.payload["artifact_type"]),
                source_type=str(point.payload["source_type"]),
                live_vacancy=bool(point.payload["live_vacancy"]),
                source=str(point.payload["source"]),
                captured_at=str(point.payload["captured_at"]),
                excerpt=str(point.payload["text"])[:300],
                score=round(float(point.score), 4),
            )
            for point in points
        ]
