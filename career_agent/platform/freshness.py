"""User-facing freshness facts for live and historical job records."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select

from .models import JobRecord
from .repository import JobRepository, utcnow


def freshness_report(repository: JobRepository) -> dict[str, Any]:
    """Return explicit data-recency facts without treating unverified as live."""
    now = utcnow()
    with repository.sessions() as session:
        last_seen = session.scalar(select(func.max(JobRecord.last_seen_at)))
        verified_24h = session.scalar(
            select(func.count()).select_from(JobRecord).where(
                JobRecord.lifecycle_status == "open",
                JobRecord.last_verified_at.is_not(None),
                JobRecord.last_verified_at >= now - timedelta(hours=24),
            )
        ) or 0
        verified_7d = session.scalar(
            select(func.count()).select_from(JobRecord).where(
                JobRecord.lifecycle_status == "open",
                JobRecord.last_verified_at.is_not(None),
                JobRecord.last_verified_at >= now - timedelta(days=7),
            )
        ) or 0
        stale_open = session.scalar(
            select(func.count()).select_from(JobRecord).where(
                JobRecord.lifecycle_status == "open",
                (JobRecord.last_verified_at.is_(None)) | (JobRecord.last_verified_at < now - timedelta(days=7)),
            )
        ) or 0

    overview = repository.overview()
    by_status = overview["by_status"]
    open_jobs = int(by_status.get("open", 0))
    unverified = int(by_status.get("unverified", 0))
    historical = int(by_status.get("historical", 0))
    return {
        "as_of": now.isoformat(),
        "latest_record_seen_at": last_seen.isoformat() if last_seen else None,
        "open_jobs": open_jobs,
        "open_verified_last_24h": int(verified_24h),
        "open_verified_last_7d": int(verified_7d),
        "stale_open_jobs": int(stale_open),
        "unverified_jobs": unverified,
        "historical_jobs": historical,
        "disclosure": (
            "Only records marked open are presented as directly actionable. "
            "Unverified and historical records are retained for market research and preparation, not as a promise that a role remains open."
        ),
    }
