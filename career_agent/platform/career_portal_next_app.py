"""Canonical API surface for the job-seeker experience.

The lifecycle service remains the system of record; this module adds user
workspace actions and an explainable read model without changing source data.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .career_intelligence import build_match_insight, clean_text, hybrid_rerank
from .career_portal_next import CAREER_PORTAL_NEXT_HTML
from .governance import governance_report
from .identity import active_profile_key
from .repository import job_to_dict
from .service import PlatformComponents, create_platform_app
from .taxonomy import classify_job, cycle_guidance
from .workspace import CareerWorkspace


class CareerMatchRequest(BaseModel):
    job_id: str = Field(min_length=1)
    resume_text: str = Field(min_length=1, max_length=40_000)


class BookmarkRequest(BaseModel):
    job_id: str = Field(min_length=1)
    note: str = Field(default="", max_length=4_000)


class ApplicationRequest(BookmarkRequest):
    stage: str = Field(default="saved", max_length=40)
    target_date: str | None = Field(default=None, max_length=32)


class SubscriptionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: str = Field(default="", max_length=500)
    filters: dict[str, Any] = Field(default_factory=dict)


_STAGES = {"saved", "applied", "assessment", "interview", "offer", "rejected", "archived"}


def _compact(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"text", "metadata", "company_key", "external_id", "status_reason"}
    }


def _filtered(records: list[dict[str, Any]], *, job_group: str, company: str, location: str) -> list[dict[str, Any]]:
    def contains(value: str, actual: object) -> bool:
        return not value or value.casefold() in str(actual or "").casefold()
    return [
        record for record in records
        if contains(job_group, record.get("job_group"))
        and contains(company, record.get("company"))
        and contains(location, record.get("location"))
    ]

_QUERY_TERMS = re.compile(r"[a-z0-9+#./-]+|[\u4e00-\u9fff]+", re.IGNORECASE)
_LATIN_TERM = re.compile(r"^[a-z0-9+#./-]+$")
_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "\u4ea7\u54c1": ("\u4ea7\u54c1", "product"),
    "\u4ea7\u54c1\u7ecf\u7406": ("\u4ea7\u54c1\u7ecf\u7406", "product manager", "product owner"),
    "\u540e\u7aef": ("\u540e\u7aef", "backend", "back-end"),
    "\u524d\u7aef": ("\u524d\u7aef", "frontend", "front-end"),
    "\u5f00\u53d1": ("\u5f00\u53d1", "developer", "software engineer"),
    "\u5de5\u7a0b\u5e08": ("\u5de5\u7a0b\u5e08", "engineer"),
    "\u7b97\u6cd5": ("\u7b97\u6cd5", "algorithm", "machine learning"),
    "\u6570\u636e\u5206\u6790": ("\u6570\u636e\u5206\u6790", "data analyst", "data analytics"),
    "\u8bbe\u8ba1": ("\u8bbe\u8ba1", "designer", "design", "ux", "ui"),
    "\u8fd0\u8425": ("\u8fd0\u8425", "operations"),
    "\u5e02\u573a": ("\u5e02\u573a", "marketing"),
    "\u8425\u9500": ("\u8425\u9500", "marketing"),
    "\u9500\u552e": ("\u9500\u552e", "sales"),
    "\u5546\u52a1": ("\u5546\u52a1", "business development", "sales"),
    "\u62db\u8058": ("\u62db\u8058", "recruiter", "recruiting", "talent acquisition"),
    "\u8d22\u52a1": ("\u8d22\u52a1", "finance", "accounting"),
    "\u6cd5\u52a1": ("\u6cd5\u52a1", "legal", "counsel"),
}

_ROLE_QUERY_GROUPS = {
    "\u4ea7\u54c1": "product", "\u4ea7\u54c1\u7ecf\u7406": "product", "\u4ea7\u54c1\u5c97": "product", "\u4ea7\u54c1\u5c97\u4f4d": "product", "product": "product", "product manager": "product", "product owner": "product",
    "\u540e\u7aef": "engineering", "backend": "engineering", "\u524d\u7aef": "engineering", "frontend": "engineering", "\u5f00\u53d1": "engineering", "\u5de5\u7a0b\u5e08": "engineering", "engineer": "engineering", "developer": "engineering",
    "\u7b97\u6cd5": "data", "machine learning": "data", "\u6570\u636e\u5206\u6790": "data", "data analyst": "data", "data scientist": "data",
    "\u8bbe\u8ba1": "design", "design": "design", "designer": "design", "ux": "design", "ui": "design",
    "\u8fd0\u8425": "operations", "operations": "operations", "\u9879\u76ee\u7ba1\u7406": "operations", "project manager": "operations",
    "\u5e02\u573a": "marketing", "\u8425\u9500": "marketing", "marketing": "marketing", "growth": "marketing",
    "\u9500\u552e": "sales", "\u5546\u52a1": "sales", "sales": "sales", "business development": "sales",
    "\u62db\u8058": "hr", "recruiter": "hr", "recruiting": "hr", "hr": "hr",
    "\u8d22\u52a1": "finance", "\u4f1a\u8ba1": "finance", "finance": "finance", "accounting": "finance",
    "\u6cd5\u52a1": "legal", "\u5408\u89c4": "legal", "legal": "legal", "compliance": "legal",
}


def _role_query_group(query: str) -> str | None:
    return _ROLE_QUERY_GROUPS.get(re.sub(r"\s+", " ", query.casefold()).strip())


def _matches_role_query(record: dict[str, Any], role_group: str | None) -> bool:
    return role_group is None or classify_job(str(record.get("title", ""))).job_group == role_group

def _terms(query: str) -> list[str]:
    """Keep exact Chinese words and Latin terms available as a precision guard."""
    return list(dict.fromkeys(_QUERY_TERMS.findall(query.casefold())))


def _contains_term(haystack: str, term: str) -> bool:
    if _LATIN_TERM.fullmatch(term):
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", haystack) is not None
    return term in haystack


def _has_all_terms(
    record: dict[str, Any],
    terms: list[str],
    fields: tuple[str, ...],
    *,
    allow_aliases: bool = False,
) -> bool:
    if not terms:
        return False
    haystack = " ".join(clean_text(str(record.get(field, ""))).casefold() for field in fields)
    return all(
        any(_contains_term(haystack, variant) for variant in (_QUERY_ALIASES.get(term, (term,)) if allow_aliases else (term,)))
        for term in terms
    )


def _in_scope(record: dict[str, Any], scope: str, campus_cycle: str, employment_kind: str) -> bool:
    return (
        (scope == "all" or (scope == "live" and record["lifecycle_status"] == "open") or (scope == "history" and record["lifecycle_status"] != "open"))
        and (not campus_cycle or record["campus_cycle"] == campus_cycle)
        and (not employment_kind or record["employment_kind"] == employment_kind)
    )

def create_career_portal_next_app(components: PlatformComponents):
    app = create_platform_app(components)
    workspace = CareerWorkspace(components.repository.engine.url.render_as_string(hide_password=False))
    workspace.create_schema()

    @app.get("/", response_class=HTMLResponse)
    def career_portal() -> str:
        return CAREER_PORTAL_NEXT_HTML

    @app.get("/api/career/search")
    def career_search(
        query: str = Query(default="", max_length=2_000),
        scope: str = Query(default="live", pattern="^(live|history|all)$"),
        limit: int | None = Query(default=None, ge=1, le=10_000),
        campus_cycle: str = "",
        employment_kind: str = "",
        job_group: str = "",
        company: str = "",
        location: str = "",
        expand_semantic: bool = False,    ) -> dict[str, Any]:
        search_query = query.strip()
        universe = [job_to_dict(record) for record in components.repository.jobs_for_index()]
        universe = [
            record
            for record in universe
            if _in_scope(record, scope, campus_cycle, employment_kind)
        ]
        universe = _filtered(universe, job_group=job_group, company=company, location=location)
        query_terms = _terms(search_query)
        role_group = _role_query_group(search_query)
        scores: dict[str, float]
        all_results = True

        if not query_terms:
            selected = universe
            scores = {str(record["id"]): 0.3 for record in selected}
            match_mode = "browse_all"
        else:
            company_exact = [
                record for record in universe if _has_all_terms(record, query_terms, ("company",))
            ]
            primary_exact = [
                record
                for record in universe
                if _has_all_terms(record, query_terms, ("title", "job_group"), allow_aliases=True) and _matches_role_query(record, role_group)
            ]
            content_exact = [
                record
                for record in universe
                if _has_all_terms(record, query_terms, ("title", "company", "job_group", "location", "text"), allow_aliases=True) and _matches_role_query(record, role_group)
            ]
            if company_exact:
                selected, match_mode = company_exact, "company_exact"
                scores = {str(record["id"]): 0.7 for record in selected}
            elif primary_exact:
                selected, match_mode = primary_exact, "title_or_category_exact"
                scores = {str(record["id"]): 0.7 for record in selected}
            elif content_exact:
                selected, match_mode = content_exact, "full_text_exact"
                scores = {str(record["id"]): 0.55 for record in selected}
            else:
                if not expand_semantic:
                    selected, scores, match_mode = [], {}, "no_exact_match"
                else:
                    try:
                        hits = components.vector_store.search(
                            search_query,
                            scope=scope,
                            limit=500,
                            campus_cycle=campus_cycle or None,
                            employment_kind=employment_kind or None,
                        )
                    except Exception:
                        hits = []
                    scores = {hit.id: hit.score for hit in hits}
                    records = {record.id: job_to_dict(record) for record in components.repository.get_many(scores)}
                    selected = [
                        record
                        for job_id, record in records.items()
                        if job_id in scores and record in universe
                    ]
                    match_mode = "semantic_expansion" if selected else "no_match"
                    all_results = False

        ranked = hybrid_rerank(search_query or "all jobs", selected, scores)
        for record in ranked:
            record.pop("text", None)
            record.pop("metadata", None)
        facets = {
            "job_groups": sorted({str(record.get("job_group")) for record in ranked}),
            "companies": sorted({str(record.get("company")) for record in ranked})[:40],
            "locations": sorted({str(record.get("location")) for record in ranked})[:40],
        }
        items = ranked if limit is None else ranked[:limit]
        return {
            "items": items,
            "total_matches": len(ranked),
            "displayed_matches": len(items),
            "all_results": all_results,
            "match_mode": match_mode,
            # Retained for existing clients that still read this field.
            "total_candidates": len(ranked),
            "facets": facets,
            "search_strategy": "strict company/title/category/full-text matching; semantic expansion only when explicitly requested; cross-source duplicates merged",
        }

    @app.get("/api/career/jobs/{job_id}")
    def career_job_detail(job_id: str) -> dict[str, Any]:
        job = components.repository.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        record = job_to_dict(job)
        return {**_compact(record), "description": clean_text(record["text"]), "source_metadata": record["metadata"]}

    @app.post("/api/career/match")
    def career_match(payload: CareerMatchRequest) -> dict[str, Any]:
        job = components.repository.get(payload.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        record = job_to_dict(job)
        return {
            "job": _compact(record),
            "match": build_match_insight(payload.resume_text, record).to_dict(),
            "cycle_guidance": cycle_guidance(job.campus_cycle, job.employment_kind),
        }

    @app.get("/api/career/data-quality")
    def career_data_quality() -> dict[str, Any]:
        return governance_report(components.repository)

    @app.post("/api/career/bookmarks")
    def save_bookmark(payload: BookmarkRequest, profile_key: str = Depends(active_profile_key)) -> dict[str, Any]:
        if components.repository.get(payload.job_id) is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return workspace.save_job(payload.job_id, payload.note, profile_key=profile_key)

    @app.delete("/api/career/bookmarks/{job_id}")
    def delete_bookmark(job_id: str, profile_key: str = Depends(active_profile_key)) -> dict[str, bool]:
        return {"removed": workspace.remove_saved_job(job_id, profile_key=profile_key)}

    @app.get("/api/career/bookmarks")
    def bookmarks(profile_key: str = Depends(active_profile_key)) -> list[dict[str, Any]]:
        output = []
        for saved in workspace.saved_jobs(profile_key=profile_key):
            job = components.repository.get(saved["job_id"])
            output.append({**saved, "job": _compact(job_to_dict(job)) if job else None})
        return output

    @app.post("/api/career/applications")
    def save_application(payload: ApplicationRequest, profile_key: str = Depends(active_profile_key)) -> dict[str, Any]:
        if payload.stage not in _STAGES:
            raise HTTPException(status_code=422, detail=f"stage must be one of {sorted(_STAGES)}")
        if components.repository.get(payload.job_id) is None:
            raise HTTPException(status_code=404, detail="Job not found")
        workspace.save_job(payload.job_id, profile_key=profile_key)
        return workspace.track_application(payload.job_id, payload.stage, payload.note, payload.target_date, profile_key=profile_key)

    @app.get("/api/career/applications")
    def applications(profile_key: str = Depends(active_profile_key)) -> list[dict[str, Any]]:
        output = []
        for item in workspace.applications(profile_key=profile_key):
            job = components.repository.get(item["job_id"])
            output.append({**item, "job_title": job.title if job else None, "company": job.company if job else None})
        return output

    @app.post("/api/career/subscriptions")
    def create_subscription(payload: SubscriptionRequest, profile_key: str = Depends(active_profile_key)) -> dict[str, Any]:
        return workspace.create_subscription(payload.name, payload.query, payload.filters, profile_key=profile_key)

    @app.get("/api/career/subscriptions")
    def subscriptions(profile_key: str = Depends(active_profile_key)) -> list[dict[str, Any]]:
        return workspace.subscriptions(profile_key=profile_key)

    return app
