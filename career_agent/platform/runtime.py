"""Production runtime factory: configured connectors plus retry policy."""

from __future__ import annotations

from .bootstrap import configured_connectors
from .config import PlatformSettings
from .orchestration import DailySyncScheduler, SyncOrchestrator
from .repository import JobRepository
from .resilience import RetryPolicy, RetryingConnector
from .service import PlatformComponents
from .vector_store import LifecycleVectorStore


def build_components(settings: PlatformSettings) -> PlatformComponents:
    repository = JobRepository(settings.database_url)
    vector_store = LifecycleVectorStore(
        repository,
        model_name=settings.embedding_model,
        qdrant_url=settings.qdrant_url,
        qdrant_path=settings.qdrant_path,
    )
    connectors = [RetryingConnector(connector, RetryPolicy(max_attempts=3)) for connector in configured_connectors(settings)]
    orchestrator = SyncOrchestrator(
        repository,
        connectors,
        vector_store=vector_store,
        missing_threshold=settings.missing_sync_threshold,
        history_retention_days=settings.history_retention_days,
    )
    return PlatformComponents(
        settings=settings,
        repository=repository,
        vector_store=vector_store,
        orchestrator=orchestrator,
        scheduler=DailySyncScheduler(orchestrator, hour_utc=settings.scheduler_hour_utc),
    )

