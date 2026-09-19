"""Canonical all-job corpus loader with strict function-group coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .large_corpus import (
    OPEN_JOBS_BATCH,
    OPEN_JOBS_MANIFEST,
    _normalise_open_jobs,
    _normalise_seed,
    iter_jsonl,
    large_coverage_report,
)
from .scalable_corpus import load_scalable_job_records


def _correct_seed_group(record: dict) -> dict:
    """Correct the four AI/Agent samples missed by the initial title rules."""
    result = _normalise_seed(record)
    if result["position"] == "other":
        title = f"{result['title']} {record.get('position', '')}".casefold()
        if any(term in title for term in ("ai", "agent", "服务端", "全栈", "应用开发")):
            result["position"] = "engineering"
            result["job_family"] = "engineering"
    return result


def load_verified_all_job_records(
    *,
    licensed_paths: Iterable[Path] | None = None,
    include_seed: bool = True,
) -> tuple[list[dict], dict[str, int]]:
    """Load only exact source identities; postings are never collapsed by company."""
    paths = list(licensed_paths) if licensed_paths is not None else [OPEN_JOBS_BATCH]
    absent = [path for path in paths if not path.exists()]
    if absent:
        raise FileNotFoundError(f"Licensed corpus batch is missing: {', '.join(map(str, absent))}")

    records: list[dict] = []
    if include_seed:
        seed_records, _ = load_scalable_job_records()
        records.extend(_correct_seed_group(record) for record in seed_records)
    for path in paths:
        records.extend(_normalise_open_jobs(raw) for raw in iter_jsonl(path))

    seen: set[tuple[str, str]] = set()
    kept: list[dict] = []
    duplicates = 0
    for record in records:
        identity = (record["source_name"], record["source_job_id"] or record["source_url"])
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        kept.append(record)
    return kept, {"exact_source_duplicates_removed": duplicates}


__all__ = [
    "OPEN_JOBS_BATCH",
    "OPEN_JOBS_MANIFEST",
    "large_coverage_report",
    "load_verified_all_job_records",
]

