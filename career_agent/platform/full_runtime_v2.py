"""Full runtime with source-aware 2027 campus taxonomy correction."""

from __future__ import annotations

import os

from .advanced_runtime import configured_official_ats_connectors
from .china_connectors import (
    JoinQuantCampusConnector,
    NvidiaCampusConnector,
    PddCampusPageConnector,
    ShopeeAiStarProgramConnector,
    ShopeeCampusPageConnector,
    ShopeeInternConnector,
)
from .china_connectors_v2 import BaiduCampus2027Connector
from .kuaishou_connector import KuaishouCampus2027Connector
from .lenovo_connector import LenovoCampusConnector
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
        connectors.append(BaiduCampus2027Connector())
    if _enabled("CAREER_AGENT_PDD_CAMPUS_ENABLED"):
        connectors.append(PddCampusPageConnector())
    if _enabled("CAREER_AGENT_SHOPEE_CAMPUS_ENABLED"):
        connectors.extend(
            [
                ShopeeCampusPageConnector(),
                ShopeeAiStarProgramConnector(),
                ShopeeInternConnector(),
            ]
        )
    if _enabled("CAREER_AGENT_JOINQUANT_CAMPUS_ENABLED"):
        connectors.append(JoinQuantCampusConnector())
    if _enabled("CAREER_AGENT_NVIDIA_CAMPUS_ENABLED"):
        connectors.append(NvidiaCampusConnector())
    if _enabled("CAREER_AGENT_LENOVO_CAMPUS_ENABLED"):
        connectors.append(LenovoCampusConnector())
    if _enabled("CAREER_AGENT_KUAISHOU_CAMPUS_ENABLED"):
        connectors.append(KuaishouCampus2027Connector())
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
