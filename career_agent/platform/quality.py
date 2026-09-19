"""Data-quality checks for lifecycle-aware job records."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select

from .models import JobRecord
from .repository import JobRepository, utcnow


def quality_report(repository: JobRepository, *, stale_after_days: int = 7) -> dict[str, Any]:
    now = utcnow()
    with repository.sessions() as session:
        stale_open = session.scalar(
            select(func.count()).select_from(JobRecord).where(
                JobRecord.lifecycle_status == "open",
                (JobRecord.last_verified_at.is_(None)) | (JobRecord.last_verified_at < now - timedelta(days=stale_after_days)),
            )
        ) or 0
        missing_url = session.scalar(
            select(func.count()).select_from(JobRecord).where(JobRecord.source_url == "")
        ) or 0
        unclassified = session.scalar(
            select(func.count()).select_from(JobRecord).where(JobRecord.employment_kind == "unknown")
        ) or 0
    overview = repository.overview()
    health = repository.source_health()
    unhealthy = [item for item in health if item["consecutive_failures"] > 0]
    return {
        "overview": overview,
        "checks": {
            "stale_open_jobs": stale_open,
            "records_missing_source_url": missing_url,
            "unclassified_employment_kind": unclassified,
            "unhealthy_sources": len(unhealthy),
        },
        "source_health": health,
    }

