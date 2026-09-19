"""One-time, auditable taxonomy refresh for records ingested by older rules."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from .models import JobRecord
from .repository import JobRepository
from .taxonomy import classify_job


@dataclass(frozen=True)
class TaxonomyBackfillResult:
    scanned: int
    changed: int
    affected_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, int | list[str]]:
        return {"scanned": self.scanned, "changed": self.changed, "affected_ids": list(self.affected_ids)}


def refresh_job_taxonomy(repository: JobRepository) -> TaxonomyBackfillResult:
    affected: list[str] = []
    scanned = 0
    with repository.sessions.begin() as session:
        for job in session.scalars(select(JobRecord)).all():
            scanned += 1
            metadata = job.metadata_json or {}
            declared_group = str(metadata.get("declared_group", ""))
            if metadata.get("taxonomy_override") == "official_2027_campus_page":
                declared_group = f"2027届校招 {declared_group}"
            taxonomy = classify_job(job.title, job.description, declared_group)
            fields_changed = (
                job.employment_kind != taxonomy.employment_kind
                or job.campus_cycle != taxonomy.campus_cycle
                or job.job_group != taxonomy.job_group
            )
            if not fields_changed:
                continue
            job.employment_kind = taxonomy.employment_kind
            job.campus_cycle = taxonomy.campus_cycle
            job.job_group = taxonomy.job_group
            job.metadata_json = {**(job.metadata_json or {}), "taxonomy_confidence": taxonomy.confidence, "taxonomy_refreshed": True}
            affected.append(job.id)
    return TaxonomyBackfillResult(scanned=scanned, changed=len(affected), affected_ids=tuple(affected))
