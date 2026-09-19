from __future__ import annotations

from career_agent.platform.connectors import IncomingJob
from career_agent.platform.repository import JobRepository
from career_agent.platform.snapshot_reconciliation import (
    NON_AUTHORITATIVE_SNAPSHOT_SOURCES,
    SNAPSHOT_ARCHIVE_REASON,
    reconcile_non_authoritative_snapshots,
    verification_report,
)


def test_snapshot_records_remain_pending_until_an_official_verifier_runs(tmp_path) -> None:
    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}")
    repository.create_schema()
    repository.apply_sync(
        "open_jobs_cc0",
        [
            IncomingJob(
                source_name="open_jobs_cc0",
                external_id="snapshot-1",
                source_url="https://example.test/snapshot-1",
                company="Snapshot",
                title="Engineer",
                description="Imported snapshot without a live feed.",
                declared_status="unknown",
            )
        ],
        authoritative=False,
        missing_threshold=2,
    )
    repository.apply_sync(
        "greenhouse:verified",
        [
            IncomingJob(
                source_name="greenhouse:verified",
                external_id="verified-1",
                source_url="https://example.test/verified-1",
                company="Verified",
                title="Engineer",
                description="Authoritative live feed.",
                declared_status="open",
            )
        ],
        authoritative=True,
        missing_threshold=2,
    )

    result = reconcile_non_authoritative_snapshots(repository)
    assert result["archived_snapshot_records"] == 0
    snapshot = next(job for job in repository.jobs_for_index() if job.source_name == "open_jobs_cc0")
    assert snapshot.lifecycle_status == "unverified"
    assert snapshot.status_reason == "source_declared_status"
    report = verification_report(repository)
    assert report["live_verified_jobs"] == 1
    assert report["unverified_jobs"] == 1
    assert report["closed_after_official_check"] == 0
    assert set(result["source_names"]) == set(NON_AUTHORITATIVE_SNAPSHOT_SOURCES)
