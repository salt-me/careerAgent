"""Auditable, cross-job-family corpus for the universal CareerAgent mode.

The corpus deliberately distinguishes an individually actionable public vacancy
from a market/job-family profile.  The latter helps a user explore occupations,
but must never be presented as a company currently hiring them.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .jd_corpus import load_curated_jds


UNIVERSAL_RECORDS_PATH = Path(__file__).resolve().parent / "data" / "universal_records.json"


def _family_for_ai_record(record: dict[str, Any]) -> str:
    text = f"{record.get('title', '')} {record.get('position', '')}".lower()
    if "infra" in text or "训练" in text:
        return "AI基础设施"
    if "agent" in text or "应用" in text or "coding" in text:
        return "AI应用工程"
    return "人工智能算法"


def _normalise_curated_ai_record(record: dict[str, Any]) -> dict[str, Any]:
    """Add the universal schema without rewriting the existing audited source."""
    return {
        **record,
        "artifact_type": "public_jd",
        "job_family": _family_for_ai_record(record),
        "experience": "以公开岗位页为准",
        "employment_type": "以公开岗位页为准",
        "source_type": "official_career_page",
        "live_vacancy": True,
        "note": "来自现有官方招聘页语料；投递前请以岗位页状态为准。",
    }


def _read_universal_records() -> list[dict[str, Any]]:
    return json.loads(UNIVERSAL_RECORDS_PATH.read_text(encoding="utf-8"))


def load_universal_records() -> list[dict[str, Any]]:
    """Return all records in a stable ordering, with globally unique IDs."""
    records = [_normalise_curated_ai_record(record) for record in load_curated_jds()]
    records.extend(_read_universal_records())
    ids = [str(record["id"]) for record in records]
    if len(ids) != len(set(ids)):
        duplicates = sorted(record_id for record_id, count in Counter(ids).items() if count > 1)
        raise ValueError(f"Duplicate universal corpus IDs: {duplicates}")
    return records


def find_universal_record(record_id: str) -> dict[str, Any]:
    for record in load_universal_records():
        if record["id"] == record_id:
            return record
    raise KeyError(f"Public JD or job-family profile not found: {record_id}")


def filter_records(
    records: Iterable[dict[str, Any]],
    *,
    job_family: str | None = None,
    artifact_type: str | None = None,
    actionable_only: bool = False,
) -> list[dict[str, Any]]:
    """Filter metadata locally as a second guard around vector retrieval."""
    result: list[dict[str, Any]] = []
    for record in records:
        if job_family and record["job_family"] != job_family:
            continue
        if artifact_type and record["artifact_type"] != artifact_type:
            continue
        if actionable_only and not record["live_vacancy"]:
            continue
        result.append(record)
    return result


def corpus_summary() -> dict[str, Any]:
    records = load_universal_records()
    by_type = Counter(record["artifact_type"] for record in records)
    by_family = Counter(record["job_family"] for record in records)
    return {
        "record_count": len(records),
        "actionable_public_jd_count": sum(1 for record in records if record["live_vacancy"]),
        "job_family_profile_count": by_type["job_family_profile"],
        "job_family_count": len(by_family),
        "records_by_artifact_type": dict(sorted(by_type.items())),
        "records_by_job_family": dict(sorted(by_family.items())),
        "disclaimer": "公开岗位页可能变更；岗位画像不等于某公司正在招聘，不能作为直接投递依据。",
    }
