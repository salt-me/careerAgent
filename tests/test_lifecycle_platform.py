from __future__ import annotations

from datetime import timedelta

from career_agent.platform.connectors import GreenhouseConnector, IncomingJob, StaticConnector
from career_agent.platform.orchestration import SyncOrchestrator
from career_agent.platform.quality import quality_report
from career_agent.platform.repository import JobRepository, utcnow
from career_agent.platform.taxonomy import classify_job


def _job(*, status: str = "open") -> IncomingJob:
    return IncomingJob(
        source_name="greenhouse:acme",
        external_id="job-1",
        source_url="https://boards.greenhouse.io/acme/jobs/1",
        company="Acme",
        title="2027届秋招 - 后端开发工程师",
        description="Python distributed systems internship and campus recruitment.",
        location="北京",
        declared_status=status,
    )


def _runtime(tmp_path, jobs):
    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'lifecycle.db'}")
    repository.create_schema()
    connector = StaticConnector("greenhouse:acme", jobs, authoritative=True)
    return repository, connector, SyncOrchestrator(
        repository,
        [connector],
        vector_store=None,
        missing_threshold=2,
        history_retention_days=1095,
    )


def test_authoritative_missing_transition_archives_only_after_second_miss(tmp_path):
    repository, connector, orchestrator = _runtime(tmp_path, [_job()])
    first = orchestrator.sync_one(connector.name)
    job_id = first.to_dict()["source_name"]
    assert first.created == 1
    stored = repository.jobs_for_index()[0]
    assert stored.lifecycle_status == "open"
    assert stored.campus_cycle == "2027_autumn"
    assert stored.employment_kind == "internship"

    connector.jobs = []
    once_missing = orchestrator.sync_one(connector.name)
    assert once_missing.archived == 0
    assert repository.jobs_for_index() == []
    first_record = repository.get(stored.id)
    assert first_record is not None and first_record.lifecycle_status == "missing"

    twice_missing = orchestrator.sync_one(connector.name)
    assert twice_missing.archived == 1
    archived = repository.get(stored.id)
    assert archived is not None and archived.lifecycle_status == "historical"
    assert archived.archived_at is not None


def test_history_retention_purges_only_old_archived_jobs(tmp_path):
    repository, connector, orchestrator = _runtime(tmp_path, [_job(status="closed")])
    orchestrator.sync_one(connector.name)
    record = repository.jobs_for_index()[0]
    # Move test clock forward beyond the configured three-year retention period.
    deleted = repository.purge_historical(1095, now=utcnow() + timedelta(days=1096))
    assert deleted == 1
    assert repository.get(record.id) is None


def test_taxonomy_handles_campus_seasons_and_non_campus_roles():
    assert classify_job("2027届秋招 产品经理", "校招").campus_cycle == "2027_autumn"
    assert classify_job("2026届春招 算法工程师", "应届毕业生").campus_cycle == "2026_spring"
    assert classify_job("后端开发实习生", "每周到岗四天").employment_kind == "internship"
    assert classify_job("Senior Backend Engineer", "5年以上 experienced").employment_kind == "experienced"


def test_greenhouse_connector_parses_public_board_payload_without_network():
    connector = GreenhouseConnector(
        "acme",
        fetch_json=lambda _: {
            "jobs": [
                {
                    "id": 12,
                    "title": "2027届秋招 Software Engineer",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/12",
                    "content": "<p>Build reliable services with Python.</p>",
                    "updated_at": "2026-08-02T00:00:00Z",
                    "location": {"name": "Shanghai"},
                    "departments": [{"name": "Engineering"}],
                }
            ]
        },
    )
    jobs = connector.fetch()
    assert len(jobs) == 1
    assert jobs[0].declared_status == "open"
    assert jobs[0].description == "Build reliable services with Python."


def test_data_quality_exposes_source_health(tmp_path):
    repository, connector, orchestrator = _runtime(tmp_path, [_job()])
    orchestrator.sync_one(connector.name)
    result = quality_report(repository)
    assert result["overview"]["total_jobs"] == 1
    assert result["source_health"][0]["consecutive_failures"] == 0
