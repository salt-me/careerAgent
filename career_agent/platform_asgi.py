"""Runnable lifecycle-platform API entry point.

Production deployment must set CAREER_AGENT_DATABASE_URL to PostgreSQL and
CAREER_AGENT_QDRANT_URL to a Qdrant server. SQLite is only the local demo
default used when neither variable is configured.
"""

from __future__ import annotations

from .platform.bootstrap import configured_connectors
from .platform.config import PlatformSettings
from .platform.orchestration import DailySyncScheduler, SyncOrchestrator
from .platform.repository import JobRepository
from .platform.service import PlatformComponents, create_platform_app
from .platform.vector_store import LifecycleVectorStore


settings = PlatformSettings.from_env()
repository = JobRepository(settings.database_url)
vector_store = LifecycleVectorStore(
    repository,
    model_name=settings.embedding_model,
    qdrant_url=settings.qdrant_url,
    qdrant_path=settings.qdrant_path,
)
orchestrator = SyncOrchestrator(
    repository,
    configured_connectors(settings),
    vector_store=vector_store,
    missing_threshold=settings.missing_sync_threshold,
    history_retention_days=settings.history_retention_days,
)
scheduler = DailySyncScheduler(orchestrator, hour_utc=settings.scheduler_hour_utc)
app = create_platform_app(
    PlatformComponents(
        settings=settings,
        repository=repository,
        vector_store=vector_store,
        orchestrator=orchestrator,
        scheduler=scheduler,
    )
)

