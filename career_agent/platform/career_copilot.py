"""Grounded job-search planning that does not fabricate hiring claims."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from .career_intelligence import extract_skills, hybrid_rerank
from .repository import JobRepository, job_to_dict
from .vector_store import LifecycleVectorStore


@dataclass(frozen=True)
class CopilotRequest:
    message: str = ""
    target_role: str = ""
    target_location: str = ""
    campus_cycle: str = ""
    employment_kind: str = ""
    resume_text: str = ""
    scope: str = "live"


@dataclass(frozen=True)
class CareerCopilot:
    repository: JobRepository
    vector_store: LifecycleVectorStore

    @staticmethod
    def _matches(request: CopilotRequest, record: dict[str, Any]) -> bool:
        location = request.target_location.casefold().strip()
        return (
            (not location or location in str(record.get("location", "")).casefold())
            and (not request.campus_cycle or record.get("campus_cycle") == request.campus_cycle)
            and (not request.employment_kind or record.get("employment_kind") == request.employment_kind)
        )

    def plan(self, request: CopilotRequest) -> dict[str, Any]:
        query = " ".join(item for item in (request.target_role.strip(), request.message.strip()) if item).strip()
        query = query or "graduate campus jobs"
        scope = request.scope if request.scope in {"live", "history", "all"} else "live"
        try:
            hits = self.vector_store.search(
                query,
                scope=scope,
                limit=30,
                campus_cycle=request.campus_cycle or None,
                employment_kind=request.employment_kind or None,
            )
        except Exception:
            hits = []

        scores = {hit.id: hit.score for hit in hits}
        records = {record.id: job_to_dict(record) for record in self.repository.get_many(scores)}
        candidates = [records[job_id] for job_id in scores if job_id in records]
        if not candidates:
            candidates = [job_to_dict(job) for job in self.repository.jobs_for_index()]
            candidates = [
                item
                for item in candidates
                if scope == "all"
                or (scope == "live" and item["lifecycle_status"] == "open")
                or (scope == "history" and item["lifecycle_status"] != "open")
            ]
            scores = {str(item["id"]): 0.3 for item in candidates}

        filtered_candidates = [item for item in candidates if self._matches(request, item)]
        filters_relaxed = bool(candidates) and not filtered_candidates
        ranked = hybrid_rerank(query, filtered_candidates or candidates, scores)
        shortlist = ranked[:5]
        resume_skills = set(extract_skills(request.resume_text))
        demanded = Counter(skill for item in shortlist for skill in extract_skills(str(item.get("text", ""))))
        missing = [skill for skill, _ in demanded.most_common() if skill not in resume_skills][:5]
        covered = [skill for skill, _ in demanded.most_common() if skill in resume_skills][:5]

        missing_text = "\u3001".join(missing[:3])
        actions = [
            "\u4f18\u5148\u6253\u5f00\u524d 3 \u4e2a\u5b9e\u65f6\u5c97\u4f4d\u7684\u5b98\u65b9\u94fe\u63a5\u786e\u8ba4\u622a\u6b62\u65f6\u95f4\u548c\u6295\u9012\u8981\u6c42\u3002",
            "\u628a\u6700\u76f8\u5173\u9879\u76ee\u7ecf\u5386\u6539\u5199\u6210\u201c\u4efb\u52a1\u2014\u65b9\u6cd5\u2014\u91cf\u5316\u7ed3\u679c\u2014\u4e2a\u4eba\u8d21\u732e\u201d\u7684\u8bc1\u636e\u94fe\u3002",
            "\u4e3a\u6bcf\u4e2a\u6280\u80fd\u7f3a\u53e3\u51c6\u5907\u4e00\u4e2a\u53ef\u9a8c\u8bc1\u4ea7\u51fa\uff0c\u4e0d\u628a\u5c1a\u672a\u638c\u63e1\u7684\u80fd\u529b\u5199\u6210\u5df2\u6709\u7ecf\u5386\u3002",
        ]
        if missing:
            actions.insert(1, f"\u672c\u8f6e\u4f18\u5148\u8865\u9f50\uff1a{missing_text}\u3002")
        if request.campus_cycle:
            actions.append(f"\u7b5b\u9009\u5df2\u9650\u5b9a\u4e3a {request.campus_cycle}\uff1b\u5c4a\u522b\u4fe1\u606f\u4ecd\u5e94\u4ee5\u5c97\u4f4d\u5b98\u65b9\u9875\u9762\u4e3a\u51c6\u3002")

        citations = [
            {
                "job_id": item["id"],
                "title": item["title"],
                "company": item["company"],
                "location": item["location"],
                "status": item["lifecycle_status"],
                "source_url": item["source_url"],
                "match_score": item.get("ranking", {}).get("score"),
            }
            for item in shortlist
        ]
        open_count = sum(item["lifecycle_status"] == "open" for item in shortlist)
        summary = (
            f"\u5df2\u57fa\u4e8e {len(ranked)} \u4e2a\u5019\u9009\u5c97\u4f4d\u751f\u6210\u672c\u8f6e\u8ba1\u5212\uff0c\u524d {len(shortlist)} \u4e2a\u4e2d\u6709 {open_count} \u4e2a\u6807\u8bb0\u4e3a\u5b9e\u65f6\u5f00\u653e\u3002"
            "\u5efa\u8bae\u628a\u5c97\u4f4d\u539f\u6587\u548c\u5b98\u65b9\u94fe\u63a5\u4f5c\u4e3a\u6295\u9012\u51b3\u7b56\u4f9d\u636e\u3002"
        )
        if filters_relaxed:
            summary += " \u672a\u627e\u5230\u5b8c\u5168\u5339\u914d\u4f60\u7684\u57ce\u5e02\u3001\u5c4a\u522b\u6216\u7c7b\u578b\u7b5b\u9009\u7684\u5c97\u4f4d\uff0c\u5df2\u5c55\u793a\u540c\u65b9\u5411\u53c2\u8003\u5c97\u4f4d\u3002"
        return {
            "mode": "grounded_career_copilot",
            "query": query,
            "scope": scope,
            "summary": summary,
            "actions": actions,
            "skills": {"covered": covered, "priority_gaps": missing},
            "citations": citations,
            "boundary": "\u5efa\u8bae\u57fa\u4e8e\u5c97\u4f4d\u6587\u672c\u3001\u7b80\u5386\u5173\u952e\u8bcd\u548c\u6570\u636e\u72b6\u6001\u751f\u6210\uff0c\u4e0d\u6784\u6210\u5f55\u7528\u9884\u6d4b\uff0c\u4e5f\u4e0d\u4f1a\u66ff\u4ee3\u5b98\u65b9\u62db\u8058\u9875\u9762\u3002",
        }

    def to_dict(self, request: CopilotRequest) -> dict[str, Any]:
        return {"request": asdict(request), "plan": self.plan(request)}