"""Honest lifecycle handling for imports without a live verification feed."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from .models import JobRecord
from .repository import JobRepository, utcnow
from .vector_store import LifecycleVectorStore


NON_AUTHORITATIVE_SNAPSHOT_SOURCES = ("open_jobs_cc0", "official_ats_cc0")
SNAPSHOT_ARCHIVE_REASON = "snapshot_not_independently_verified"


def reconcile_non_authoritative_snapshots(
    repository: JobRepository,
    vector_store: LifecycleVectorStore | None = None,
) -> dict[str, Any]:
    """Deprecated compatibility entrypoint: snapshot records are never auto-archived.

    Call ``run_snapshot_verification`` instead.  Unsupported URLs remain in the
    verification queue until a source-specific official verifier is available.
    """
    del vector_store
    report = verification_report(repository)
    return {
        "archived_snapshot_records": 0,
        "history_payloads_updated": 0,
        "reason": "verification_required_no_automatic_archive",
        "source_names": list(NON_AUTHORITATIVE_SNAPSHOT_SOURCES),
        "verification": report,
    }

def verification_report(repository: JobRepository) -> dict[str, Any]:
    """Expose authoritative results separately from unsupported verification work."""
    with repository.sessions() as session:
        live_verified = session.scalar(
            select(func.count()).select_from(JobRecord).where(JobRecord.lifecycle_status == "open")
        ) or 0
        verified_from_snapshots = session.scalar(
            select(func.count()).select_from(JobRecord).where(
                JobRecord.lifecycle_status == "open",
                JobRecord.status_reason == "official_ats_api_verified_open",
            )
        ) or 0
        closed_from_snapshots = session.scalar(
            select(func.count()).select_from(JobRecord).where(
                JobRecord.lifecycle_status == "historical",
                JobRecord.status_reason == "official_ats_api_not_listed",
            )
        ) or 0
        pending_by_reason = dict(
            session.execute(
                select(JobRecord.status_reason, func.count())
                .where(JobRecord.lifecycle_status == "unverified")
                .group_by(JobRecord.status_reason)
            ).all()
        )
    pending = sum(int(value) for value in pending_by_reason.values())
    unsupported = int(pending_by_reason.get("unsupported_official_source", 0))
    failed = sum(
        int(value)
        for reason, value in pending_by_reason.items()
        if str(reason or "").startswith("official_") and str(reason or "").endswith("_verification_failed")
    )
    return {
        "live_verified_jobs": int(live_verified),
        "verified_from_snapshot_urls": int(verified_from_snapshots),
        "closed_after_official_check": int(closed_from_snapshots),
        "unverified_jobs": int(pending),
        "pending_unsupported_source": unsupported,
        "pending_fetch_failure": failed,
        "pending_by_reason": {str(reason or "unknown"): int(value) for reason, value in pending_by_reason.items()},
        "policy": "A job is marked open or closed only after its own official ATS board responds successfully. Unsupported sources remain explicitly pending until a source-specific official verifier is added.",
    }