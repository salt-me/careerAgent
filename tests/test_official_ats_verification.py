from __future__ import annotations

from career_agent.platform.connectors import IncomingJob
from career_agent.platform.official_ats_verification import VerificationTarget, verify_targets
from career_agent.platform.repository import JobRepository
from career_agent.platform.snapshot_reconciliation import reconcile_non_authoritative_snapshots
from career_agent.platform.verification_service import run_snapshot_verification


def _live_job(url: str) -> IncomingJob:
    return IncomingJob(
        source_name="greenhouse:acme",
        external_id="1",
        source_url=url,
        company="Acme",
        title="Engineer",
        description="Live official job.",
        declared_status="open",
    )


def test_verifier_only_closes_jobs_after_a_successful_board_response() -> None:
    targets = [
        VerificationTarget("open", "https://boards.greenhouse.io/acme/jobs/1", "greenhouse", "acme"),
        VerificationTarget("closed", "https://boards.greenhouse.io/acme/jobs/2", "greenhouse", "acme"),
        VerificationTarget("unsupported", "https://careers.example.test/jobs/3", None, None),
        VerificationTarget("failed", "https://jobs.lever.co/failing/4", "lever", "failing"),
    ]

    def fetch(provider: str, board: str):
        if board == "failing":
            raise OSError("temporary failure")
        assert provider == "greenhouse" and board == "acme"
        return [_live_job("https://boards.greenhouse.io/acme/jobs/1?gh_jid=1")]

    result = verify_targets(targets, fetch_board=fetch, max_workers=1)
    assert result.verified_open_ids == ("open",)
    assert result.verified_closed_ids == ("closed",)
    assert result.pending_ids_by_reason["unsupported_official_source"] == ("unsupported",)
    assert result.pending_ids_by_reason["official_lever_verification_failed"] == ("failed",)


def test_service_restores_snapshot_then_records_open_closed_and_pending(tmp_path) -> None:
    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}")
    repository.create_schema()
    repository.apply_sync(
        "open_jobs_cc0",
        [
            IncomingJob("open_jobs_cc0", "open", "https://boards.greenhouse.io/acme/jobs/1", "Acme", "Engineer", "", declared_status="unknown"),
            IncomingJob("open_jobs_cc0", "closed", "https://boards.greenhouse.io/acme/jobs/2", "Acme", "Engineer", "", declared_status="unknown"),
            IncomingJob("open_jobs_cc0", "pending", "https://careers.example.test/jobs/3", "Acme", "Engineer", "", declared_status="unknown"),
        ],
        authoritative=False,
        missing_threshold=2,
    )
    reconcile_non_authoritative_snapshots(repository)

    result = run_snapshot_verification(
        repository,
        fetch_board=lambda _provider, _board: [_live_job("https://boards.greenhouse.io/acme/jobs/1")],
        max_workers=1,
    )
    by_external = {job.external_id: job for job in repository.jobs_for_index()}
    assert result["restored_for_verification"] == 0
    assert result["verified_open"] == 1
    assert result["verified_closed"] == 1
    assert by_external["open"].lifecycle_status == "open"
    assert by_external["closed"].lifecycle_status == "historical"
    assert by_external["pending"].lifecycle_status == "unverified"
    assert by_external["pending"].status_reason == "unsupported_official_source"
