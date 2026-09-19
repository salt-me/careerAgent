"""Application service for re-verifying imported public ATS URLs."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from .models import JobRecord
from .official_ats_verification import BoardFetcher, target_from_record, verify_targets
from .repository import JobRepository, utcnow
from .snapshot_reconciliation import NON_AUTHORITATIVE_SNAPSHOT_SOURCES, SNAPSHOT_ARCHIVE_REASON
from .vector_store import LifecycleVectorStore


def run_snapshot_verification(
    repository: JobRepository,
    vector_store: LifecycleVectorStore | None = None,
    *,
    fetch_board: BoardFetcher | None = None,
    max_workers: int = 6,
) -> dict[str, Any]:
    """Restore snapshot records, verify supported URLs, and retain honest pending states."""
    observed_at = utcnow()
    restored_ids = repository.restore_snapshot_records_for_verification(
        NON_AUTHORITATIVE_SNAPSHOT_SOURCES,
        archived_reason=SNAPSHOT_ARCHIVE_REASON,
    )
    with repository.sessions() as session:
        records = session.scalars(
            select(JobRecord).where(
                JobRecord.source_name.in_(NON_AUTHORITATIVE_SNAPSHOT_SOURCES),
                JobRecord.lifecycle_status == "unverified",
            )
        ).all()
    batch = verify_targets((target_from_record(record) for record in records), fetch_board=fetch_board, max_workers=max_workers)
    applied = repository.apply_official_verification(
        verified_open_ids=batch.verified_open_ids,
        verified_closed_ids=batch.verified_closed_ids,
        provider="ats_api",
    )
    pending_updated = {
        reason: repository.mark_verification_pending(ids, reason=reason, observed_at=observed_at)
        for reason, ids in batch.pending_ids_by_reason.items()
    }
    vector_updates: dict[str, int] = {"promoted_open": 0, "marked_historical": 0}
    if vector_store is not None:
        if batch.verified_open_ids:
            vector_updates["promoted_open"] = vector_store.promote_verified_open_jobs(
                repository.get_many(batch.verified_open_ids)
            )
        if batch.verified_closed_ids:
            vector_updates["marked_historical"] = vector_store.mark_historical_payloads(
                batch.verified_closed_ids,
                archived_at=observed_at.isoformat(),
                reason="official_ats_api_not_listed",
            )
    return {
        "restored_for_verification": len(restored_ids),
        "targets_considered": len(records),
        "verified_open": applied["open"],
        "verified_closed": applied["closed"],
        "pending_by_reason": {reason: len(ids) for reason, ids in batch.pending_ids_by_reason.items()},
        "pending_statuses_updated": pending_updated,
        "board_attempts": batch.board_attempts,
        "board_failures": batch.board_failures,
        "vector_updates": vector_updates,
    }
