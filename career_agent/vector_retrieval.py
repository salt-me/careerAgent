"""Dense embeddings and persistent local Qdrant storage for curated public JDs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from .public_jds import load_public_jds


MODEL_NAME = "BAAI/bge-small-zh-v1.5"
COLLECTION_NAME = "career_agent_public_jds"
DEFAULT_STORAGE = Path(__file__).resolve().parents[1] / "qdrant_storage" / "career_agent_public"


@dataclass(frozen=True)
class PublicJDRetrievalHit:
    id: str
    title: str
    company: str
    position: str
    location: str
    source: str
    captured_at: str
    excerpt: str
    score: float


class PublicJDVectorStore:
    """Local Qdrant collection backed by the Chinese BGE-small embedding model."""

    def __init__(self, storage_path: str | Path = DEFAULT_STORAGE) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(self.storage_path))
        self.embedding = TextEmbedding(model_name=MODEL_NAME)

    @staticmethod
    def _as_lists(vectors: Iterable[Any]) -> list[list[float]]:
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]

    def rebuild(self) -> dict[str, str | int]:
        jobs = load_public_jds()
        vectors = self._as_lists(self.embedding.embed([job["text"] for job in jobs]))
        if not vectors:
            raise RuntimeError("公开 JD 语料为空，无法建立向量库。")
        self.client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
        )
        points = [
            models.PointStruct(
                id=index,
                vector=vector,
                payload={key: value for key, value in job.items() if key != "id"} | {"job_id": job["id"]},
            )
            for index, (job, vector) in enumerate(zip(jobs, vectors, strict=True))
        ]
        self.client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        return {"collection": COLLECTION_NAME, "documents": len(points), "model": MODEL_NAME, "storage": str(self.storage_path)}

    def is_ready(self) -> bool:
        return self.client.collection_exists(COLLECTION_NAME)

    def search(self, query: str, limit: int = 3) -> list[PublicJDRetrievalHit]:
        if not self.is_ready():
            raise RuntimeError("向量库尚未建立，请先调用 rebuild。")
        vector = self._as_lists(self.embedding.embed([query]))[0]
        points = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=limit,
            with_payload=True,
        ).points
        return [
            PublicJDRetrievalHit(
                id=str(point.payload["job_id"]),
                title=str(point.payload["title"]),
                company=str(point.payload["company"]),
                position=str(point.payload["position"]),
                location=str(point.payload["location"]),
                source=str(point.payload["source"]),
                captured_at=str(point.payload["captured_at"]),
                excerpt=str(point.payload["text"])[:300],
                score=round(float(point.score), 4),
            )
            for point in points
        ]
