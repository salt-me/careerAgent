"""Public, read-only connector for Kuaishou's 2027 campus board."""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any, Callable

from .connectors import IncomingJob


JsonFetcher = Callable[[str, dict[str, Any]], dict[str, Any]]


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://campus.kuaishou.cn",
            "Referer": "https://campus.kuaishou.cn/recruit/campus/e/h5/",
            "User-Agent": "CareerAgent/1.0 (official-job-board-sync)",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


class KuaishouCampus2027Connector:
    """Synchronize the public, currently-listed 2027 Kuaishou campus jobs."""

    name = "kuaishou:campus-2027-public-api"
    authoritative = True
    endpoint = "https://campus.kuaishou.cn/recruit/campus/e/api/v1/open/positions/simple"
    sub_project_code = "20271779425607"

    def __init__(self, *, fetch_json: JsonFetcher | None = None) -> None:
        self._fetch_json = fetch_json or _post_json

    def fetch(self) -> list[IncomingJob]:
        payload = self._fetch_json(
            self.endpoint,
            {"pageNum": 1, "pageSize": 100, "recruitSubProjectCodes": [self.sub_project_code]},
        )
        if payload.get("code") != 0 or not isinstance(payload.get("result"), dict):
            raise ValueError(f"Kuaishou public positions API returned an unexpected response: {payload.get('message')}")
        result = payload["result"]
        total = result.get("total")
        records = result.get("list")
        if not isinstance(records, list) or not isinstance(total, int) or total > len(records):
            raise ValueError("Kuaishou public positions API returned an incomplete page")

        jobs: list[IncomingJob] = []
        for row in records:
            if not isinstance(row, dict):
                continue
            identifier = _text(row.get("id"))
            title = _text(row.get("name"))
            if not identifier or not title:
                continue
            location = "、".join(
                _text(item.get("name"))
                for item in row.get("workLocationDicts") or []
                if isinstance(item, dict) and _text(item.get("name"))
            ) or "not_disclosed"
            description = "\n".join(
                part for part in (_text(row.get("description")), _text(row.get("positionDemand"))) if part
            ) or title
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=identifier,
                    source_url=(
                        "https://campus.kuaishou.cn/recruit/campus/e/h5/"
                        f"#/campus/job-info/{identifier}?recruitSubProjectCodes={self.sub_project_code}"
                    ),
                    company="快手",
                    title=title,
                    description=description,
                    location=location,
                    declared_status="open",
                    published_at=_text(row.get("releaseTime")) or None,
                    declared_group="2027届校招",
                    metadata={
                        "connector": "kuaishou_public_positions_api",
                        "official_api": self.endpoint,
                        "recruit_project_code": _text(row.get("recruitProjectCode")),
                        "recruit_sub_project_code": _text(row.get("recruitSubProjectCode")),
                        "position_category_code": _text(row.get("positionCategoryCode")),
                        "position_status_code": _text(row.get("positionStatusCode")),
                    },
                ).with_inferred_language()
            )
        return jobs
