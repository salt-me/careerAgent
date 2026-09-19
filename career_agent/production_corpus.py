"""Canonical production corpus: CC0 10k base plus audited Chinese platform batches."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from .large_corpus import _normalise_open_jobs, _stable_id, iter_jsonl, large_coverage_report
from .verified_all_job_corpus import load_verified_all_job_records


LICENSED_SOURCE_DIR = Path(__file__).resolve().parent / "data" / "licensed_sources"
NOWCODER_CAREER_BATCH = LICENSED_SOURCE_DIR / "nowcoder_careers_413_public.jsonl"


def _platform_group(title: str, direction: str) -> str:
    """Map Nowcoder page taxonomies to the already-audited all-job groups."""
    value = f"{title} {direction}".casefold()
    if any(term in value for term in ("数据", "算法", "机器学习", "人工智能", "ai", "挖掘")):
        return "data"
    if any(term in value for term in ("产品", "用户研究")):
        return "product"
    if any(term in value for term in ("设计", "ui", "ux")):
        return "design"
    if any(term in value for term in ("人力", "招聘", "hr")):
        return "hr"
    if any(term in value for term in ("财务", "会计", "审计")):
        return "finance"
    if any(term in value for term in ("销售", "商务", "bd")):
        return "sales"
    if any(term in value for term in ("运营", "项目管理", "供应链", "行政")):
        return "ops"
    # 后端、前端、测试、客户端、运维及未细分的技术岗均归入 engineering。
    if any(term in value for term in ("开发", "工程", "测试", "运维", "安卓", "ios", "技术", "架构")):
        return "engineering"
    return "ops"


def _normalise_platform_record(raw: dict) -> dict:
    """Reuse the full-record validator while keeping the original platform identity."""
    record = _normalise_open_jobs(raw)
    source_name = str(raw.get("source_name") or "nowcoder").casefold()
    source_job_id = str(raw["source_job_id"])
    record["id"] = _stable_id(source_name, source_job_id, record["source_url"])
    record["source_name"] = source_name
    record["source_provider"] = str(raw.get("source_provider") or source_name)
    record["source_license"] = str(raw.get("source_license") or "public-page-summary")
    record["source_status"] = str(raw.get("source_status") or "unknown").casefold()
    record["live_vacancy"] = record["source_status"] == "open"
    record["source_page"] = str(raw.get("source_page") or record["source_url"])
    record["source_position"] = str(raw.get("position") or "not_disclosed")
    record["position"] = _platform_group(record["title"], record["source_position"])
    record["job_family"] = record["position"]
    record["language"] = "zh"
    return record


def load_production_job_records(
    *,
    platform_paths: Iterable[Path] | None = None,
) -> tuple[list[dict], dict[str, int]]:
    """Load the verified base and retain distinct platform jobs by source job ID."""
    paths = list(platform_paths) if platform_paths is not None else [NOWCODER_CAREER_BATCH]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Audited Chinese platform batch is missing: {', '.join(map(str, missing))}")
    records, base_deduplication = load_verified_all_job_records()
    records = list(records)
    for path in paths:
        records.extend(_normalise_platform_record(raw) for raw in iter_jsonl(path))

    identities: set[tuple[str, str]] = set()
    kept: list[dict] = []
    duplicates = 0
    for record in records:
        identity = (record["source_name"], record["source_job_id"] or record["source_url"])
        if identity in identities:
            duplicates += 1
            continue
        identities.add(identity)
        kept.append(record)
    return kept, {
        **base_deduplication,
        "platform_exact_source_duplicates_removed": duplicates,
    }


def production_report(records: Iterable[dict]) -> dict:
    report = large_coverage_report(records)
    historical_platform_records = [
        record
        for record in records
        if record["source_name"] != "open_jobs_cc0" and record.get("source_provider") == "nowcoder"
    ]
    report["chinese_platform_summary"] = {
        "nowcoder_record_count": len(historical_platform_records),
        "nowcoder_different_company_count": len({record["company_key"] for record in historical_platform_records}),
        "nowcoder_group_distribution": dict(Counter(record["position"] for record in historical_platform_records)),
        "status": "historical public-page records are marked closed and are not live-job recommendations",
    }
    return report

