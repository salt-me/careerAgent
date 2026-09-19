from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.platform.config import PlatformSettings
from career_agent.platform.connectors import IncomingJob, StaticConnector
from career_agent.platform.orchestration import SyncOrchestrator
from career_agent.platform.repository import JobRepository
from career_agent.platform.service import PlatformComponents, create_platform_app


class StubVectorStore:
    def search(self, *_args, **_kwargs):
        return []


def test_admin_health_and_match_api(tmp_path):
    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'api.db'}")
    repository.create_schema()
    connector = StaticConnector(
        "test-source",
        [
            IncomingJob(
                source_name="test-source",
                external_id="1",
                source_url="https://jobs.example.test/1",
                company="Example",
                title="2027届秋招 Java Engineer",
                description="Java SQL distributed systems campus job.",
                declared_status="open",
            )
        ],
    )
    settings = PlatformSettings(
        database_url="sqlite",
        qdrant_url=None,
        qdrant_path=tmp_path / "qdrant",
        embedding_model="unused",
        missing_sync_threshold=2,
        history_retention_days=1095,
        admin_token=None,
        scheduler_enabled=False,
        scheduler_hour_utc=2,
        greenhouse_boards=(),
    )
    orchestrator = SyncOrchestrator(
        repository, [connector], vector_store=None, missing_threshold=2, history_retention_days=1095
    )
    orchestrator.sync_one("test-source")
    app = create_platform_app(
        PlatformComponents(settings, repository, StubVectorStore(), orchestrator)  # type: ignore[arg-type]
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/admin").status_code == 200
        job_id = repository.jobs_for_index()[0].id
        response = client.post("/api/jobs/match", json={"resume_text": "Java SQL", "job_id": job_id})
        assert response.status_code == 200
        assert response.json()["job"]["campus_cycle"] == "2027_autumn"
