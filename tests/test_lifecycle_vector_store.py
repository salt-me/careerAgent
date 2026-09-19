from __future__ import annotations

from career_agent.platform.connectors import IncomingJob
from career_agent.platform.repository import JobRepository
from career_agent.platform.vector_store import HISTORY_COLLECTION, LIVE_COLLECTION, LifecycleVectorStore


class FakeEmbedding:
    def embed(self, texts):
        for text in texts:
            yield [float(len(text) % 11), 1.0, 0.5]


def _job(external_id: str, status: str) -> IncomingJob:
    return IncomingJob(
        source_name="official-test",
        external_id=external_id,
        source_url=f"https://jobs.example.test/{external_id}",
        company=f"Company {external_id}",
        title="Data Engineer",
        description=f"SQL Python data pipeline {external_id}",
        declared_status=status,
    )


def test_live_and_history_qdrant_collections_are_separate(tmp_path):
    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'vectors.db'}")
    repository.create_schema()
    repository.apply_sync("official-test", [_job("live", "open"), _job("history", "closed")], authoritative=False, missing_threshold=2)
    store = LifecycleVectorStore(repository, model_name="fake", qdrant_path=tmp_path / "qdrant")
    store._embedding = FakeEmbedding()  # type: ignore[assignment]

    stats = store.rebuild()
    assert stats["live"] == 1
    assert stats["history"] == 1
    assert store.client.collection_exists(LIVE_COLLECTION)
    assert store.client.collection_exists(HISTORY_COLLECTION)
    assert {hit.lifecycle_status for hit in store.search("SQL Python", scope="live")} == {"open"}
    assert {hit.lifecycle_status for hit in store.search("SQL Python", scope="history")} == {"historical"}
