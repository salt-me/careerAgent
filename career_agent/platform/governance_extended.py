"""Non-truncated metrics used by the production portal status cards."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .career_intelligence import canonical_job_key
from .governance import governance_report
from .repository import JobRepository, job_to_dict


def exact_cross_source_duplicate_count(repository: JobRepository) -> int:
    sources_by_key: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(int)
    for job in repository.jobs_for_index():
        record = job_to_dict(job)
        key = canonical_job_key(record)
        counts[key] += 1
        sources_by_key[key].add(str(record["source_name"]))
    return sum(1 for key, count in counts.items() if count > 1 and len(sources_by_key[key]) > 1)


def production_governance_report(repository: JobRepository) -> dict[str, Any]:
    report = governance_report(repository)
    report["governance"]["cross_source_duplicate_clusters"] = exact_cross_source_duplicate_count(repository)
    report["governance"]["duplicate_candidates_limit"] = len(report["governance"]["duplicate_candidates"])
    return report
