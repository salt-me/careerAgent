from __future__ import annotations

from sqlalchemy import select

from career_agent.platform.models import JobRecord
from career_agent.platform.taxonomy_backfill import refresh_job_taxonomy


def test_taxonomy_backfill_repairs_preexisting_record(platform_components) -> None:
    job = platform_components.repository.jobs_for_index()[0]
    with platform_components.repository.sessions.begin() as session:
        row = session.scalar(select(JobRecord).where(JobRecord.id == job.id))
        assert row is not None
        row.title = "3年经验财务主管（社招）"
        row.description = "负责财务分析与报表。"
        row.employment_kind, row.campus_cycle, row.job_group = "unknown", "not_applicable", "other"
    result = refresh_job_taxonomy(platform_components.repository)
    repaired = platform_components.repository.get(job.id)
    assert result.changed == 1
    assert repaired is not None
    assert (repaired.employment_kind, repaired.job_group) == ("experienced", "finance")
