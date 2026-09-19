"""Unified loader for the 10k licensed all-job public-JD corpus.

The local Chinese public samples remain useful for the product demonstration.
The CC0 Open Jobs batch supplies the volume and occupation breadth.  This
loader intentionally preserves multiple distinct postings from one company;
deduplication is by source job identifier or exact source URL, never by
company/title/location alone.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

from .scalable_corpus import (
    MIN_COMPANIES_PER_POSITION,
    TARGET_RECORD_COUNT,
    canonical_company,
    load_scalable_job_records,
)


LICENSED_SOURCE_DIR = Path(__file__).resolve().parent / "data" / "licensed_sources"
OPEN_JOBS_BATCH = LICENSED_SOURCE_DIR / "open_jobs_cc0_10000.jsonl"
OPEN_JOBS_MANIFEST = LICENSED_SOURCE_DIR / "open_jobs_cc0_10000.manifest.json"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _stable_id(source_name: str, source_job_id: str, source_url: str) -> str:
    basis = source_job_id or source_url
    digest = hashlib.sha256(f"{source_name}:{basis}".encode("utf-8")).hexdigest()[:20]
    return f"{source_name}-{digest}"


def _detect_language(text: str) -> str:
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    if cjk_count >= 20 and cjk_count >= latin_count * 0.2:
        return "zh"
    if latin_count >= 20:
        return "en"
    return "unknown"


def _broad_group(title: str, position: str) -> str:
    """Map legacy Chinese samples into the Open Jobs source's broad function taxonomy."""
    value = f"{title} {position}".casefold()
    mappings = (
        ("engineering", ("后端", "前端", "java", "golang", "算法", "大模型", "人工智能", "测试", "运维", "sre", "devops", "数据工程")),
        ("data", ("数据分析", "bi")),
        ("product", ("产品",)),
        ("sales", ("销售", "商务", "bd")),
        ("hr", ("人力", "招聘", "hrbp")),
        ("finance", ("财务", "会计")),
        ("design", ("设计", "ui", "ux")),
        ("ops", ("运营",)),
    )
    for group, terms in mappings:
        if any(term in value for term in terms):
            return group
    return "other"


def _normalise_open_jobs(raw: dict[str, Any]) -> dict[str, Any]:
    required = ("source_url", "source_job_id", "title", "company", "position", "text", "captured_at")
    missing = [field for field in required if not _clean(raw.get(field))]
    if missing:
        raise ValueError(f"CC0 Open Jobs record missing required fields: {', '.join(missing)}")
    text = _clean(raw["text"])
    if len(text) < 40:
        raise ValueError("CC0 Open Jobs record has no usable JD text")
    source_url = _clean(raw["source_url"])
    source_job_id = _clean(raw["source_job_id"])
    company = _clean(raw["company"])
    position = _clean(raw["position"]).casefold()
    return {
        "id": _stable_id("open_jobs_cc0", source_job_id, source_url),
        "artifact_type": "public_jd",
        "source_name": "open_jobs_cc0",
        "source_provider": _clean(raw.get("source_provider", "open-jobs")),
        "source_license": _clean(raw.get("source_license", "CC0-1.0")),
        "source_url": source_url,
        "source_job_id": source_job_id,
        "source_status": _clean(raw.get("source_status", "unknown")).casefold() or "unknown",
        "title": _clean(raw["title"]),
        "company": company,
        "company_key": canonical_company(company),
        "position": position,
        "job_family": _clean(raw.get("job_family")) or position,
        "location": _clean(raw.get("location", "not_disclosed")) or "not_disclosed",
        "experience": _clean(raw.get("experience", "not_disclosed")) or "not_disclosed",
        "employment_type": _clean(raw.get("employment_type", "not_disclosed")) or "not_disclosed",
        "published_at": _clean(raw.get("published_at", "not_disclosed")) or "not_disclosed",
        "captured_at": _clean(raw["captured_at"]),
        "live_vacancy": False,
        "language": _detect_language(text),
        "text": text,
        "source_note": _clean(raw.get("source_note"))
        or "CC0 Open Jobs snapshot; verify the retained original ATS URL before applying.",
    }


def _normalise_seed(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["position"] = _broad_group(result["title"], result.get("position", ""))
    result["job_family"] = result["position"]
    result["language"] = _detect_language(result["text"])
    result["source_license"] = "public-page-summary"
    result["source_provider"] = result["source_name"]
    return result


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path.name}:{line_number} is not valid JSON") from error


def load_large_job_records(
    *,
    licensed_paths: Iterable[Path] | None = None,
    include_seed: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Load the licensed 10k corpus and retain only exact source duplicates."""
    paths = list(licensed_paths) if licensed_paths is not None else [OPEN_JOBS_BATCH]
    missing_paths = [path for path in paths if not path.exists()]
    if missing_paths:
        missing = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"Licensed corpus batch is missing: {missing}. Run open_jobs_cc0_cli_v2 first.")

    records: list[dict[str, Any]] = []
    if include_seed:
        seed_records, _ = load_scalable_job_records()
        records.extend(_normalise_seed(record) for record in seed_records)
    for path in paths:
        records.extend(_normalise_open_jobs(raw) for raw in iter_jsonl(path))

    kept: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for record in records:
        identity = (record["source_name"], record["source_job_id"] or record["source_url"])
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        kept.append(record)
    return kept, {"exact_source_duplicates_removed": duplicates}


def large_coverage_report(
    records: Iterable[dict[str, Any]],
    *,
    target_record_count: int = TARGET_RECORD_COUNT,
    min_companies_per_position: int = MIN_COMPANIES_PER_POSITION,
) -> dict[str, Any]:
    records = list(records)
    companies_by_position: defaultdict[str, set[str]] = defaultdict(set)
    record_count_by_position: Counter[str] = Counter()
    source_distribution: Counter[str] = Counter()
    language_distribution: Counter[str] = Counter()
    for record in records:
        position = record["position"]
        companies_by_position[position].add(record["company_key"])
        record_count_by_position[position] += 1
        source_distribution[record["source_name"]] += 1
        language_distribution[record.get("language", "unknown")] += 1
    positions = {
        position: {
            "record_count": record_count_by_position[position],
            "different_company_count": len(companies),
            "meets_minimum": len(companies) >= min_companies_per_position,
            "companies_needed": max(0, min_companies_per_position - len(companies)),
        }
        for position, companies in sorted(companies_by_position.items())
    }
    below_minimum = {name: detail for name, detail in positions.items() if not detail["meets_minimum"]}
    return {
        "record_count": len(records),
        "target_record_count": target_record_count,
        "records_needed": max(0, target_record_count - len(records)),
        "source_distribution": dict(sorted(source_distribution.items())),
        "language_distribution": dict(sorted(language_distribution.items())),
        "position_group_definition": "Open Jobs structured function; legacy Chinese samples are mapped to the same broad function taxonomy.",
        "position_group_count": len(positions),
        "minimum_companies_per_position_group": min_companies_per_position,
        "positions": positions,
        "positions_below_company_minimum": below_minimum,
        "all_position_groups_meet_company_minimum": not below_minimum,
    }

