"""Scalable, provenance-first corpus loader for public job descriptions.

This module is intentionally separate from the first 41-record demonstration
corpus.  It accepts versioned source files, validates every record, removes
near-duplicates, and reports whether a job position has enough *different
companies*.  It never fabricates vacancies to satisfy a volume target.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .universal_corpus import load_universal_records


DATA_DIR = Path(__file__).resolve().parent / "data"
EXTERNAL_SOURCE_DIR = DATA_DIR / "external_sources"
TARGET_RECORD_COUNT = 10_000
MIN_COMPANIES_PER_POSITION = 10
SUPPORTED_SOURCES = {"liepin", "nowcoder", "baidu", "xiaohongshu", "boss", "official_company"}

_POSITION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("后端研发工程师", ("后端", "后台", "java开发", "java工程师", "golang", "服务端")),
    ("前端研发工程师", ("前端", "web开发", "web前端")),
    ("数据分析师", ("数据分析", "bi分析")),
    ("数据工程师", ("数据开发", "数仓", "数据平台")),
    ("产品经理", ("产品经理", "产品工程")),
    ("测试工程师", ("测试", "qa", "质量保障")),
    ("运维/SRE工程师", ("运维", "sre", "devops")),
    ("算法工程师", ("算法", "大模型", "机器学习", "人工智能")),
    ("运营专员", ("运营",)),
    ("销售/商务", ("销售", "商务", "bd")),
    ("人力资源", ("人力", "招聘", "hrbp")),
    ("财务会计", ("财务", "会计")),
    ("UI/UX设计师", ("ui", "ux", "交互设计", "视觉设计")),
)

_FAMILY_BY_POSITION = {
    "后端研发工程师": "后端研发",
    "前端研发工程师": "前端研发",
    "数据分析师": "数据分析",
    "数据工程师": "数据工程",
    "产品经理": "产品管理",
    "测试工程师": "测试与质量",
    "运维/SRE工程师": "运维与云原生",
    "算法工程师": "人工智能算法",
    "运营专员": "运营增长",
    "销售/商务": "销售与商务",
    "人力资源": "人力资源",
    "财务会计": "财务会计",
    "UI/UX设计师": "设计与用户体验",
}


class CorpusValidationError(ValueError):
    """Raised when one raw source record does not meet the public-corpus contract."""


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def canonical_company(company: str) -> str:
    company = _clean(company).casefold()
    company = re.sub(r"[（(].*?[)）]", "", company)
    company = re.sub(r"(股份)?有限公司$|有限责任公司$|集团$", "", company)
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", company)


def canonical_position(title: str, position: str = "") -> str:
    candidate = f"{title} {position}".casefold()
    for normalised, aliases in _POSITION_RULES:
        if any(alias in candidate for alias in aliases):
            return normalised
    return _clean(position) or _clean(title)


def infer_job_family(position: str) -> str:
    return _FAMILY_BY_POSITION.get(position, "其他岗位")


def _normalise_source_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def _stable_id(source: str, source_url: str) -> str:
    digest = hashlib.sha256(f"{source}:{_normalise_source_url(source_url)}".encode("utf-8")).hexdigest()[:16]
    return f"{source}-{digest}"


def validate_and_normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate an auditable external record and convert it to a retrieval record."""
    required = ("source_name", "source_url", "title", "company", "location", "text", "captured_at")
    missing = [field for field in required if not _clean(raw.get(field))]
    if missing:
        raise CorpusValidationError(f"Missing required fields: {', '.join(missing)}")
    source_name = _clean(raw["source_name"]).casefold()
    if source_name not in SUPPORTED_SOURCES:
        raise CorpusValidationError(f"Unsupported source_name: {source_name}")
    source_url = _clean(raw["source_url"])
    parsed = urlparse(source_url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise CorpusValidationError("source_url must be an absolute HTTP(S) URL")
    text = _clean(raw["text"])
    if len(text) < 30:
        raise CorpusValidationError("text must contain at least 30 characters of a manual public-page summary")
    try:
        date.fromisoformat(_clean(raw["captured_at"]))
    except ValueError as error:
        raise CorpusValidationError("captured_at must use YYYY-MM-DD") from error
    status = _clean(raw.get("source_status", "unknown")).casefold()
    if status not in {"open", "closed", "unknown"}:
        raise CorpusValidationError("source_status must be open, closed, or unknown")

    title = _clean(raw["title"])
    position = canonical_position(title, _clean(raw.get("position")))
    company = _clean(raw["company"])
    return {
        "id": _stable_id(source_name, source_url),
        "artifact_type": "public_jd",
        "source_name": source_name,
        "source_url": source_url,
        "source_job_id": _clean(raw.get("source_job_id")) or None,
        "source_status": status,
        "title": title,
        "company": company,
        "company_key": canonical_company(company),
        "position": position,
        "job_family": _clean(raw.get("job_family")) or infer_job_family(position),
        "location": _clean(raw["location"]),
        "experience": _clean(raw.get("experience", "not_disclosed")),
        "employment_type": _clean(raw.get("employment_type", "not_disclosed")),
        "published_at": _clean(raw.get("published_at", "not_disclosed")),
        "captured_at": _clean(raw["captured_at"]),
        "live_vacancy": status == "open",
        "text": text,
        "source_note": _clean(raw.get("source_note", "Public page manually reviewed; check the source page before applying.")),
    }


def _baseline_records() -> list[dict[str, Any]]:
    """Bring existing official-company records forward with the scalable schema."""
    records: list[dict[str, Any]] = []
    for item in load_universal_records():
        if item.get("artifact_type") != "public_jd":
            continue
        source_url = str(item["source"])
        domain = urlparse(source_url).netloc
        source_name = "baidu" if "baidu" in domain else "xiaohongshu" if "xiaohongshu" in domain else "official_company"
        records.append(
            validate_and_normalise(
                {
                    "source_name": source_name,
                    "source_url": source_url,
                    "source_job_id": item.get("id"),
                    "source_status": "open" if item.get("live_vacancy") else "unknown",
                    "title": item["title"],
                    "company": item["company"],
                    "position": item.get("position"),
                    "job_family": item.get("job_family"),
                    "location": item["location"],
                    "experience": item.get("experience"),
                    "employment_type": item.get("employment_type"),
                    "published_at": item.get("published_at"),
                    "captured_at": item["captured_at"],
                    "text": item["text"],
                    "source_note": item.get("note"),
                }
            )
        )
    return records


def iter_external_raw_records(directory: Path = EXTERNAL_SOURCE_DIR) -> Iterable[dict[str, Any]]:
    if not directory.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise CorpusValidationError(f"{path.name} must be a JSON array")
        records.extend(loaded)
    for path in sorted(directory.glob("*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise CorpusValidationError(f"{path.name}:{line_number} is invalid JSON") from error
    return records


def deduplicate(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep a single source record per company/position/location, with source URL as identity."""
    ordered = sorted(records, key=lambda record: (record["captured_at"], record["id"]), reverse=True)
    kept: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_company_position: set[tuple[str, str, str]] = set()
    url_duplicates = 0
    company_position_duplicates = 0
    for record in ordered:
        url_key = _normalise_source_url(record["source_url"])
        company_key = (record["company_key"], record["position"], record["location"].casefold())
        if url_key in seen_urls:
            url_duplicates += 1
            continue
        if company_key in seen_company_position:
            company_position_duplicates += 1
            continue
        seen_urls.add(url_key)
        seen_company_position.add(company_key)
        kept.append(record)
    return sorted(kept, key=lambda record: record["id"]), {
        "url_duplicates_removed": url_duplicates,
        "company_position_duplicates_removed": company_position_duplicates,
    }


def load_scalable_job_records() -> tuple[list[dict[str, Any]], dict[str, int]]:
    raw_external = list(iter_external_raw_records())
    external = [validate_and_normalise(raw) for raw in raw_external]
    return deduplicate([*_baseline_records(), *external])


def coverage_report(
    records: Iterable[dict[str, Any]],
    *,
    target_record_count: int = TARGET_RECORD_COUNT,
    min_companies_per_position: int = MIN_COMPANIES_PER_POSITION,
) -> dict[str, Any]:
    records = list(records)
    companies_by_position: defaultdict[str, set[str]] = defaultdict(set)
    sources = Counter()
    for record in records:
        companies_by_position[record["position"]].add(record["company_key"])
        sources[record["source_name"]] += 1
    positions = {
        position: {
            "record_count": sum(1 for record in records if record["position"] == position),
            "different_company_count": len(companies),
            "meets_minimum": len(companies) >= min_companies_per_position,
            "companies_needed": max(0, min_companies_per_position - len(companies)),
        }
        for position, companies in sorted(companies_by_position.items())
    }
    below_minimum = {position: detail for position, detail in positions.items() if not detail["meets_minimum"]}
    return {
        "record_count": len(records),
        "target_record_count": target_record_count,
        "records_needed": max(0, target_record_count - len(records)),
        "source_distribution": dict(sorted(sources.items())),
        "position_count": len(positions),
        "minimum_companies_per_position": min_companies_per_position,
        "positions": positions,
        "positions_below_company_minimum": below_minimum,
        "all_positions_meet_company_minimum": not below_minimum,
    }
