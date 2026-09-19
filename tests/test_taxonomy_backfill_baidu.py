from __future__ import annotations

from sqlalchemy import select

from career_agent.platform.models import JobRecord
from career_agent.platform.taxonomy_backfill import refresh_job_taxonomy


def test_taxonomy_backfill_preserves_official_baidu_2027_override(platform_components) -> None:
    job = platform_components.repository.jobs_for_index()[0]
    with platform_components.repository.sessions.begin() as session:
        row = session.scalar(select(JobRecord).where(JobRecord.id == job.id))
        assert row is not None
        row.title = "智能体算法工程师"
        row.description = "负责算法研发"
        row.metadata_json = {"taxonomy_override": "official_2027_campus_page"}
        row.employment_kind, row.campus_cycle, row.job_group = "unknown", "not_applicable", "other"
    refresh_job_taxonomy(platform_components.repository)
    repaired = platform_components.repository.get(job.id)
    assert repaired is not None
    assert (repaired.employment_kind, repaired.campus_cycle) == ("campus", "2027_campus_unspecified")
