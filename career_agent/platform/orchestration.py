"""Verified runtime orchestration for incremental sync and daily scheduling."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable

from apscheduler.schedulers.background import BackgroundScheduler

from .connectors import JobConnector
from .repository import JobRepository
from .vector_store import LifecycleVectorStore


@dataclass(frozen=True)
class ConnectorRunResult:
    source_name: str
    state: str
    fetched: int
    created: int
    updated: int
    archived: int
    indexed_live: int = 0
    indexed_history: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class SyncOrchestrator:
    def __init__(
        self,
        repository: JobRepository,
        connectors: Iterable[JobConnector],
        *,
        vector_store: LifecycleVectorStore | None,
        missing_threshold: int,
        history_retention_days: int,
    ) -> None:
        self.repository = repository
        self.connectors = {connector.name: connector for connector in connectors}
        self.vector_store = vector_store
        self.missing_threshold = missing_threshold
        self.history_retention_days = history_retention_days

    def sync_one(self, source_name: str) -> ConnectorRunResult:
        connector = self.connectors[source_name]
        run_id = self.repository.begin_run(source_name)
        try:
            jobs = connector.fetch()
            stats = self.repository.apply_sync(
                source_name,
                jobs,
                authoritative=connector.authoritative,
                missing_threshold=self.missing_threshold,
            )
            self.repository.record_health(source_name, success=True, record_count=stats.fetched)
            indexed = {"live": 0, "history": 0}
            if self.vector_store and stats.affected_ids:
                indexed = self.vector_store.sync_jobs(self.repository.get_many(stats.affected_ids))
            self.repository.finish_run(run_id, stats=stats)
            return ConnectorRunResult(
                source_name=source_name,
                state="succeeded",
                fetched=stats.fetched,
                created=stats.created,
                updated=stats.updated,
                archived=stats.archived,
                indexed_live=indexed["live"],
                indexed_history=indexed["history"],
            )
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            self.repository.record_health(source_name, success=False, record_count=None, error=message)
            self.repository.finish_run(run_id, error=message)
            return ConnectorRunResult(
                source_name=source_name,
                state="failed",
                fetched=0,
                created=0,
                updated=0,
                archived=0,
                error=message,
            )

    def sync_all(self) -> list[ConnectorRunResult]:
        results = [self.sync_one(name) for name in self.connectors]
        self.repository.purge_historical(self.history_retention_days)
        return results


class DailySyncScheduler:
    def __init__(self, orchestrator: SyncOrchestrator, *, hour_utc: int, after_sync: Callable[[], object] | None = None) -> None:
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.orchestrator = orchestrator
        self.hour_utc = hour_utc
        self.after_sync = after_sync

    def _run_daily(self) -> list[ConnectorRunResult]:
        results = self.orchestrator.sync_all()
        if self.after_sync:
            try:
                self.after_sync()
            except Exception:
                # Notification delivery must not make a verified data sync fail.
                pass
        return results

    def start(self) -> None:
        self.scheduler.add_job(
            self._run_daily,
            trigger="cron",
            hour=self.hour_utc,
            minute=0,
            id="career-agent-daily-sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

