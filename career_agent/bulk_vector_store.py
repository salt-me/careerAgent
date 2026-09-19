"""Batch-oriented Qdrant builder designed for a 10,000+ public-JD corpus."""

from __future__ import annotations

from itertools import islice
from pathlib import Path
from typing import Any, Iterable, Iterator

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from .scalable_corpus import load_scalable_job_records
from .vector_retrieval import MODEL_NAME


COLLECTION_NAME = "career_agent_public_jobs_v2"
DEFAULT_STORAGE = Path(__file__).resolve().parents[1] / "qdrant_storage" / "career_agent_jobs_v2"


def _chunks(items: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    iterator = iter(items)
    while chunk := list(islice(iterator, size)):
        yield chunk


class BulkJobVectorStore:
    def __init__(self, storage_path: str | Path = DEFAULT_STORAGE) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(self.storage_path))
        self.embedding = TextEmbedding(model_name=MODEL_NAME)

    @staticmethod
    def _as_lists(vectors: Iterable[Any]) -> list[list[float]]:
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]

    def rebuild(self, *, embedding_batch_size: int = 128, upsert_batch_size: int = 256) -> dict[str, Any]:
        records, deduplication = load_scalable_job_records()
        if not records:
            raise ValueError("No validated public JD records found")
        first_batch = records[:embedding_batch_size]
        first_vectors = self._as_lists(self.embedding.embed([record["text"] for record in first_batch]))
        if self.client.collection_exists(COLLECTION_NAME):
            self.client.delete_collection(COLLECTION_NAME)
        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=len(first_vectors[0]), distance=models.Distance.COSINE),
        )
        indexed = 0
        pending: list[models.PointStruct] = []
        for start, batch in enumerate(_chunks(records, embedding_batch_size)):
            vectors = first_vectors if start == 0 else self._as_lists(self.embedding.embed([record["text"] for record in batch]))
            pending.extend(
                models.PointStruct(id=indexed + offset, vector=vector, payload=record)
                for offset, (record, vector) in enumerate(zip(batch, vectors, strict=True))
            )
            indexed += len(batch)
            while len(pending) >= upsert_batch_size:
                self.client.upsert(COLLECTION_NAME, points=pending[:upsert_batch_size], wait=True)
                pending = pending[upsert_batch_size:]
        if pending:
            self.client.upsert(COLLECTION_NAME, points=pending, wait=True)
        return {
            "collection": COLLECTION_NAME,
            "documents": indexed,
            "embedding_batch_size": embedding_batch_size,
            "upsert_batch_size": upsert_batch_size,
            "model": MODEL_NAME,
            "deduplication": deduplication,
            "storage": str(self.storage_path),
        }
