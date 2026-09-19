"""Connector for Lenovo China's public job-listing endpoint.

The employer's public ``/position`` page fetches this paginated endpoint in
the browser.  It exposes a stable job ID, the complete JD, and the reported
total, so the connector enumerates every public row before reporting a
successful authoritative sync.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Callable

from .connectors import IncomingJob, _strip_html, _text


LenovoJsonFetcher = Callable[[str, dict[str, Any]], dict[str, Any]]


def _http_get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CareerAgent/1.0; official-job-board-sync)",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://talent.lenovo.com.cn/position",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    if not isinstance(payload, dict):
        raise ValueError("Lenovo public job endpoint returned a non-object payload")
    return payload


class LenovoCampusConnector:
    """Import the complete public job list on Lenovo China's career site."""

    authoritative = True
    name = "lenovo:china-public-jobbase-api"
    company = "联想"
    page_url = "https://talent.lenovo.com.cn/position"
    endpoint = "https://talent.lenovo.com.cn/gateway/jobBase/list"
    detail_url = "https://talent.lenovo.com.cn/position/detail?id={job_id}"
    page_size = 100

    def __init__(self, *, fetch_json: LenovoJsonFetcher | None = None) -> None:
        self._fetch_json = fetch_json or _http_get_json

    @staticmethod
    def _location(record: dict[str, Any]) -> str:
        """Use a textual location when the public response includes one.

        The current endpoint otherwise returns only the same city codes used
        by the official UI.  Those codes stay in metadata rather than being
        guessed as city names.
        """

        for key in ("workPlaceName", "workPlaceNames", "cityName", "location"):
            value = _text(record.get(key))
            if value:
                return value
        return "not_disclosed"

    def fetch(self) -> list[IncomingJob]:
        page, total, records, seen_ids = 1, None, [], set()
        while total is None or len(records) < total:
            payload = self._fetch_json(self.endpoint, {"pageSize": self.page_size, "pageNum": page})
            if payload.get("code") != 0:
                raise ValueError("Lenovo public job endpoint returned a non-success response")
            result = payload.get("result")
            page_records = result.get("rows") if isinstance(result, dict) else None
            if not isinstance(page_records, list):
                raise ValueError("Lenovo public job endpoint returned an invalid position list")
            try:
                response_total = int(result.get("total"))
            except (TypeError, ValueError):
                raise ValueError("Lenovo public job endpoint did not provide a total count") from None
            if response_total < len(records):
                raise ValueError("Lenovo public job endpoint total decreased during pagination")
            total = response_total
            if not page_records and len(records) < total:
                raise ValueError("Lenovo public job endpoint returned an incomplete page")

            for record in page_records:
                if not isinstance(record, dict):
                    raise ValueError("Lenovo public job endpoint returned a non-object position")
                job_id = _text(record.get("id"))
                title = _text(record.get("jobName"))
                if not job_id or not title:
                    raise ValueError("Lenovo public job endpoint returned a position without an ID or title")
                if job_id in seen_ids:
                    raise ValueError(f"Lenovo public job endpoint repeated position {job_id} on page {page}")
                seen_ids.add(job_id)
                records.append(record)
            page += 1

        if total is None or len(records) != total:
            raise ValueError(f"Lenovo public job endpoint expected {total} positions but received {len(records)}")

        jobs: list[IncomingJob] = []
        for record in records:
            job_id = _text(record.get("id"))
            title = _text(record.get("jobName"))
            duties = _strip_html(_text(record.get("jobDuties")))
            requirements = _strip_html(_text(record.get("jobRequirement")))
            category = _text(record.get("typeName"))
            project_type = _text(record.get("projectType"))
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=job_id,
                    source_url=self.detail_url.format(job_id=job_id),
                    company=self.company,
                    title=title,
                    description="\n".join(part for part in (duties, requirements) if part) or title,
                    location=self._location(record),
                    declared_status="open",
                    declared_group=" ".join(part for part in ("联想公开招聘", category) if part),
                    metadata={
                        "connector": "lenovo_china_public_jobbase_api",
                        "coverage": "complete public paginated job list",
                        "reported_total": str(total),
                        "project_type": project_type,
                        "category": category,
                        "department_id": _text(record.get("firstDeptId")),
                        "education_required": _text(record.get("educationRequired")),
                        "work_place_codes": _text(record.get("workPlace")),
                        "hot": bool(record.get("hotFlag")),
                    },
                ).with_inferred_language()
            )
        return jobs
