"""Evaluate saved search subscriptions without sending messages externally."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .career_intelligence import hybrid_rerank
from .repository import JobRepository, job_to_dict


def subscription_preview(repository: JobRepository, subscription: dict[str, Any], *, fresh_hours: int = 24, limit: int = 20) -> dict[str, Any]:
    filters = subscription.get("filters") or {}
    scope = str(filters.get("scope") or "live")
    campus = str(filters.get("campus_cycle") or "")
    kind = str(filters.get("employment_kind") or "")
    group = str(filters.get("job_group") or "")
    company = str(filters.get("company") or "").casefold()
    location = str(filters.get("location") or "").casefold()
    records = [job_to_dict(job) for job in repository.jobs_for_index()]
    if scope == "live":
        records = [record for record in records if record["lifecycle_status"] == "open"]
    elif scope == "history":
        records = [record for record in records if record["lifecycle_status"] != "open"]
    records = [
        record for record in records
        if (not campus or record["campus_cycle"] == campus)
        and (not kind or record["employment_kind"] == kind)
        and (not group or record["job_group"] == group)
        and (not company or company in record["company"].casefold())
        and (not location or location in record["location"].casefold())
    ]
    ranked = hybrid_rerank(str(subscription.get("query") or "job"), records, {str(record["id"]): 0.3 for record in records})
    cutoff = datetime.now(timezone.utc) - timedelta(hours=fresh_hours)
    fresh = 0
    for record in ranked:
        try:
            seen = datetime.fromisoformat(str(record.get("last_seen_at")).replace("Z", "+00:00"))
            fresh += seen.replace(tzinfo=seen.tzinfo or timezone.utc) >= cutoff
        except ValueError:
            continue
    return {"subscription_id": subscription["id"], "matched_count": len(ranked), "fresh_count": fresh, "fresh_window_hours": fresh_hours, "items": ranked[:limit]}
