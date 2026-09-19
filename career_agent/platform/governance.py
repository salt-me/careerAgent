"""Cross-source deduplication candidates, source alerts and quality metrics."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from .career_intelligence import canonical_job_key, clean_text
from .quality import quality_report
from .repository import JobRepository, job_to_dict


def duplicate_clusters(records: Iterable[dict[str, Any]], *, limit: int = 100) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        buckets[canonical_job_key(record)].append(record)
    clusters = []
    for key, members in buckets.items():
        sources = sorted({str(member.get("source_name", "")) for member in members})
        if len(members) > 1 and len(sources) > 1:
            clusters.append({
                "canonical_key": key,
                "company": members[0].get("company", ""),
                "title": members[0].get("title", ""),
                "count": len(members),
                "sources": sources,
                "job_ids": [str(member.get("id")) for member in members],
            })
    return sorted(clusters, key=lambda item: (-item["count"], item["company"], item["title"]))[:limit]


def source_alerts(source_health: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    alerts: list[dict[str, Any]] = []
    for item in source_health:
        failures = int(item.get("consecutive_failures") or 0)
        last_success = item.get("last_success_at")
        if failures:
            alerts.append({"level": "critical" if failures >= 3 else "warning", "source_name": item["source_name"], "code": "sync_failures", "message": f"连续同步失败 {failures} 次"})
        if last_success:
            try:
                dt = datetime.fromisoformat(str(last_success).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if (now - dt).total_seconds() > 48 * 3600:
                    alerts.append({"level": "warning", "source_name": item["source_name"], "code": "stale_source", "message": "超过 48 小时没有成功同步"})
            except ValueError:
                alerts.append({"level": "warning", "source_name": item["source_name"], "code": "invalid_timestamp", "message": "来源健康时间格式异常"})
    return alerts


def governance_report(repository: JobRepository) -> dict[str, Any]:
    base = quality_report(repository)
    records = [job_to_dict(job) for job in repository.jobs_for_index()]
    raw_markup = sum(1 for record in records if "<" in str(record.get("text", "")) and ">" in str(record.get("text", "")))
    short_description = sum(1 for record in records if len(clean_text(str(record.get("text", "")))) < 80)
    duplicates = duplicate_clusters(records)
    health = base["source_health"]
    return {
        **base,
        "governance": {
            "indexed_records_checked": len(records),
            "raw_markup_descriptions": raw_markup,
            "short_descriptions": short_description,
            "cross_source_duplicate_clusters": len(duplicates),
            "duplicate_candidates": duplicates,
            "source_alerts": source_alerts(health),
            "deduplication_policy": "同公司同规范化职位名的跨来源岗位仅在搜索结果展示一个代表记录，保留全部原始记录供审计。",
        },
    }
