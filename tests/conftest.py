from __future__ import annotations

import pytest

from career_agent.platform.config import PlatformSettings
from career_agent.platform.connectors import IncomingJob, StaticConnector
from career_agent.platform.orchestration import SyncOrchestrator
from career_agent.platform.repository import JobRepository
from career_agent.platform.service import PlatformComponents


class StubVectorStore:
    def search(self, *_args, **_kwargs):
        return []


@pytest.fixture
def platform_components(tmp_path) -> PlatformComponents:
    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'portal.db'}")
    repository.create_schema()
    connector = StaticConnector(
        "portal-test-source",
        [
            IncomingJob(
                source_name="portal-test-source",
                external_id="portal-1",
                source_url="https://jobs.example.test/portal-1",
                company="Example",
                title="2027届软件工程师",
                description="Python SQL distributed systems campus role.",
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
    orchestrator.sync_one(connector.name)
    return PlatformComponents(settings, repository, StubVectorStore(), orchestrator)  # type: ignore[arg-type]
