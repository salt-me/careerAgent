"""Runtime that combines configured Greenhouse, Lever and Ashby job boards."""

from __future__ import annotations

import os

from .bootstrap import configured_connectors
from .config import PlatformSettings
from .official_ats_connectors import AshbyConnector, LeverConnector
from .orchestration import DailySyncScheduler, SyncOrchestrator
from .repository import JobRepository
from .resilience import RetryPolicy, RetryingConnector
from .service import PlatformComponents
from .vector_store import LifecycleVectorStore


def _env_list(name: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, "").split(",") if value.strip())


def configured_official_ats_connectors(settings: PlatformSettings):
    """Build connectors from explicit allowlists, never by discovering arbitrary sites."""
    return [
        *configured_connectors(settings),
        *(LeverConnector(site) for site in _env_list("CAREER_AGENT_LEVER_SITES")),
        *(AshbyConnector(board) for board in _env_list("CAREER_AGENT_ASHBY_BOARDS")),
    ]


def build_advanced_components(settings: PlatformSettings) -> PlatformComponents:
    repository = JobRepository(settings.database_url)
    vector_store = LifecycleVectorStore(
        repository,
        model_name=settings.embedding_model,
        qdrant_url=settings.qdrant_url,
        qdrant_path=settings.qdrant_path,
    )
    connectors = [
        RetryingConnector(connector, RetryPolicy(max_attempts=3))
        for connector in configured_official_ats_connectors(settings)
    ]
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
