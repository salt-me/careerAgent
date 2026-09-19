"""Full runtime including configured overseas ATS and Chinese official pages."""

from __future__ import annotations

import os

from .advanced_runtime import configured_official_ats_connectors
from .china_connectors import BaiduCampusPageConnector
from .config import PlatformSettings
from .orchestration import DailySyncScheduler, SyncOrchestrator
from .repository import JobRepository
from .resilience import RetryPolicy, RetryingConnector
from .service import PlatformComponents
from .vector_store import LifecycleVectorStore


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().casefold() in {"1", "true", "yes", "on"}


def build_full_components(settings: PlatformSettings) -> PlatformComponents:
    repository = JobRepository(settings.database_url)
    vector_store = LifecycleVectorStore(
        repository,
        model_name=settings.embedding_model,
        qdrant_url=settings.qdrant_url,
        qdrant_path=settings.qdrant_path,
    )
    connectors = configured_official_ats_connectors(settings)
    if _enabled("CAREER_AGENT_BAIDU_CAMPUS_ENABLED"):
        connectors.append(BaiduCampusPageConnector())
    retried_connectors = [RetryingConnector(connector, RetryPolicy(max_attempts=3)) for connector in connectors]
    orchestrator = SyncOrchestrator(
        repository,
        retried_connectors,
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
