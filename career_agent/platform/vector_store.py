"""Separate live and history Qdrant collections with incremental lifecycle updates."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from .models import JobRecord
from .repository import JobRepository, job_to_dict


LIVE_COLLECTION = "career_agent_live_jobs_v1"
HISTORY_COLLECTION = "career_agent_history_jobs_v1"


def _embedding_text(job: JobRecord) -> str:
    return "\n".join((f"Title: {job.title}", f"Company: {job.company}", f"Group: {job.job_group}", job.description[:6000]))


def _point_id(job_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"career-agent-platform:{job_id}"))


@dataclass(frozen=True)
class SearchHit:
    id: str
    title: str
    company: str
    job_group: str
    lifecycle_status: str
    campus_cycle: str
    employment_kind: str
    source_name: str
    source_url: str
    score: float
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LifecycleVectorStore:
    def __init__(
        self,
        repository: JobRepository,
        *,
        model_name: str,
        qdrant_url: str | None = None,
        qdrant_path: Path | None = None,
    ) -> None:
        self.repository = repository
        self.model_name = model_name
        self.client = QdrantClient(url=qdrant_url) if qdrant_url else QdrantClient(path=str(qdrant_path or Path("qdrant_storage/lifecycle")))
        self._embedding: TextEmbedding | None = None

    @property
    def embedding(self) -> TextEmbedding:
        if self._embedding is None:
            self._embedding = TextEmbedding(model_name=self.model_name)
        return self._embedding

    @staticmethod
    def _as_lists(vectors: Iterable[Any]) -> list[list[float]]:
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]

    def _ensure_collection(self, name: str, vector_size: int) -> None:
        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )

    def _delete(self, collection: str, job_ids: Iterable[str]) -> None:
        ids = [_point_id(job_id) for job_id in job_ids]
        if ids and self.client.collection_exists(collection):
            self.client.delete(collection_name=collection, points_selector=models.PointIdsList(points=ids), wait=True)

    def sync_jobs(self, jobs: Iterable[JobRecord]) -> dict[str, int]:
        jobs = list(jobs)
        active = [job for job in jobs if job.lifecycle_status == "open"]
        history = [job for job in jobs if job.lifecycle_status in {"historical", "unverified"}]
        missing = [job for job in jobs if job.lifecycle_status == "missing"]
        self._delete(LIVE_COLLECTION, [job.id for job in history + missing])
        self._delete(HISTORY_COLLECTION, [job.id for job in active + missing])
        indexed_live = self._upsert(LIVE_COLLECTION, active)
        indexed_history = self._upsert(HISTORY_COLLECTION, history)
        return {"live": indexed_live, "history": indexed_history, "removed": len(missing)}

    def _upsert(self, collection: str, jobs: list[JobRecord]) -> int:
        if not jobs:
            return 0
        indexed = 0
        for start in range(0, len(jobs), 128):
            batch = jobs[start : start + 128]
            vectors = self._as_lists(self.embedding.embed([_embedding_text(job) for job in batch]))
            points = [
                models.PointStruct(
                    id=_point_id(job.id),
                    vector=vector,
                    payload=job_to_dict(job),
                )
                for job, vector in zip(batch, vectors, strict=True)
            ]
            for attempt in range(3):
                try:
                    self._ensure_collection(collection, len(vectors[0]))
                    self.client.upsert(collection_name=collection, points=points, wait=True)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2**attempt)
            indexed += len(points)
        return indexed

    def promote_verified_open_jobs(self, jobs: Iterable[JobRecord]) -> int:
        """Move newly verified records from history to the live collection."""
        records = [job for job in jobs if job.lifecycle_status == "open"]
        self._delete(HISTORY_COLLECTION, [job.id for job in records])
        return self._upsert(LIVE_COLLECTION, records)
    def refresh_job_group_payloads(self, jobs: Iterable[JobRecord]) -> int:
        """Refresh role-family payloads in-place after a taxonomy backfill."""
        grouped: dict[tuple[str, str], list[str]] = {}
        for job in jobs:
            collection = LIVE_COLLECTION if job.lifecycle_status == "open" else HISTORY_COLLECTION
            grouped.setdefault((collection, job.job_group), []).append(job.id)
        updated = 0
        for (collection, job_group), ids in grouped.items():
            if not self.client.collection_exists(collection):
                continue
            for start in range(0, len(ids), 256):
                batch = ids[start : start + 256]
                self.client.set_payload(
                    collection_name=collection,
                    payload={"job_group": job_group},
                    points=[_point_id(job_id) for job_id in batch],
                    wait=True,
                )
                updated += len(batch)
        return updated
    def mark_historical_payloads(self, job_ids: Iterable[str], *, archived_at: str, reason: str) -> int:
        """Update history-index lifecycle payloads without recomputing embeddings."""
        ids = list(dict.fromkeys(job_ids))
        if not ids or not self.client.collection_exists(HISTORY_COLLECTION):
            return 0
        for start in range(0, len(ids), 256):
            self.client.set_payload(
                collection_name=HISTORY_COLLECTION,
                payload={
                    "lifecycle_status": "historical",
                    "status_reason": reason,
                    "archived_at": archived_at,
                },
                points=[_point_id(job_id) for job_id in ids[start : start + 256]],
                wait=True,
            )
        return len(ids)
    def rebuild(self) -> dict[str, int]:
        records = self.repository.jobs_for_index()
        for collection in (LIVE_COLLECTION, HISTORY_COLLECTION):
            if self.client.collection_exists(collection):
                self.client.delete_collection(collection)
        result = self.sync_jobs(records)
        return {**result, "source_records": len(records)}

    def search(
        self,
        query: str,
        *,
        scope: str = "live",
        limit: int = 10,
        campus_cycle: str | None = None,
        employment_kind: str | None = None,
    ) -> list[SearchHit]:
        collections = {
            "live": (LIVE_COLLECTION,),
            "history": (HISTORY_COLLECTION,),
            "all": (LIVE_COLLECTION, HISTORY_COLLECTION),
        }.get(scope)
        if collections is None:
            raise ValueError("scope must be live, history, or all")
        available_collections = tuple(collection for collection in collections if self.client.collection_exists(collection))
        if not available_collections:
            return []
        vector = self._as_lists(self.embedding.embed([query]))[0]
        conditions: list[models.FieldCondition] = []
        if campus_cycle:
            conditions.append(models.FieldCondition(key="campus_cycle", match=models.MatchValue(value=campus_cycle)))
        if employment_kind:
            conditions.append(models.FieldCondition(key="employment_kind", match=models.MatchValue(value=employment_kind)))
        query_filter = models.Filter(must=conditions) if conditions else None
        hits: list[SearchHit] = []
        for collection in available_collections:
            points = self.client.query_points(
                collection_name=collection, query=vector, query_filter=query_filter, limit=limit, with_payload=True
            ).points
            hits.extend(
                SearchHit(
                    id=str(point.payload["id"]),
                    title=str(point.payload["title"]),
                    company=str(point.payload["company"]),
                    job_group=str(point.payload["job_group"]),
                    lifecycle_status=str(point.payload["lifecycle_status"]),
                    campus_cycle=str(point.payload["campus_cycle"]),
                    employment_kind=str(point.payload["employment_kind"]),
                    source_name=str(point.payload["source_name"]),
                    source_url=str(point.payload["source_url"]),
                    score=round(float(point.score), 4),
                    excerpt=str(point.payload["text"])[:300],
                )
                for point in points
            )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

