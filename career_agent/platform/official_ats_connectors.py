"""Additional public, official ATS connectors.

Each connector only reads the job board intentionally exposed by the employer's
ATS.  A successful fetch is authoritative: a job absent in later successful
responses is eligible for the normal lifecycle close-and-archive flow.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from .connectors import IncomingJob, _strip_html, _text


JsonFetcher = Callable[[str], Any]


def _http_get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "CareerAgent/1.0 (+official-job-board-sync)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _millis_to_iso(value: Any) -> str | None:
    try:
        timestamp = float(value) / 1000
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


class LeverConnector:
    """Read published positions from Lever's public Postings API."""

    authoritative = True

    def __init__(self, site: str, *, fetch_json: JsonFetcher | None = None) -> None:
        self.site = site
        self.name = f"lever:{site}"
        self._fetch_json = fetch_json or _http_get_json

    def fetch(self) -> list[IncomingJob]:
        payload = self._fetch_json(f"https://api.lever.co/v0/postings/{self.site}?mode=json")
        if not isinstance(payload, list):
            raise ValueError(f"Lever {self.site} returned an unexpected payload")

        jobs: list[IncomingJob] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            external_id = _text(item.get("id"))
            title = _text(item.get("text"))
            source_url = _text(item.get("hostedUrl")) or _text(item.get("applyUrl"))
            if not all((external_id, title, source_url)):
                continue
            categories = item.get("categories") if isinstance(item.get("categories"), dict) else {}
            department = _text(categories.get("department"))
            team = _text(categories.get("team"))
            description = _text(
                item.get("descriptionPlain")
                or item.get("descriptionBodyPlain")
                or _strip_html(_text(item.get("description")))
                or item.get("openingPlain")
            )
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=external_id,
                    source_url=source_url,
                    company=self.site,
                    title=title,
                    description=description or title,
                    location=_text(categories.get("location"), "not_disclosed"),
                    declared_status="open",
                    published_at=_millis_to_iso(item.get("createdAt")),
                    declared_group=" ".join(part for part in (department, team) if part),
                    metadata={
                        "connector": "lever",
                        "site": self.site,
                        "department": department,
                        "team": team,
                        "commitment": _text(categories.get("commitment")),
                        "workplace_type": _text(item.get("workplaceType")),
                    },
                ).with_inferred_language()
            )
        return jobs


class AshbyConnector:
    """Read listed positions from Ashby's public job-board endpoint."""

    authoritative = True

    def __init__(self, board: str, *, fetch_json: JsonFetcher | None = None) -> None:
        self.board = board
        self.name = f"ashby:{board}"
        self._fetch_json = fetch_json or _http_get_json

    def fetch(self) -> list[IncomingJob]:
        payload = self._fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{self.board}")
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError(f"Ashby {self.board} returned an unexpected payload")

        jobs: list[IncomingJob] = []
        for item in payload["jobs"]:
            if not isinstance(item, dict) or item.get("isListed") is False:
                continue
            external_id = _text(item.get("id"))
            title = _text(item.get("title"))
            source_url = _text(item.get("jobUrl")) or _text(item.get("applyUrl"))
            if not all((external_id, title, source_url)):
                continue
            department = _text(item.get("department"))
            team = _text(item.get("team"))
            description = _text(item.get("descriptionPlain")) or _strip_html(_text(item.get("descriptionHtml")))
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=external_id,
                    source_url=source_url,
                    company=self.board,
                    title=title,
                    description=description or title,
                    location=_text(item.get("location"), "not_disclosed"),
                    declared_status="open",
                    published_at=_text(item.get("publishedAt")) or None,
                    declared_group=" ".join(part for part in (department, team) if part),
                    metadata={
                        "connector": "ashby",
                        "board": self.board,
                        "department": department,
                        "team": team,
                        "employment_type": _text(item.get("employmentType")),
                        "workplace_type": _text(item.get("workplaceType")),
                        "remote": bool(item.get("isRemote")),
                    },
                ).with_inferred_language()
            )
        return jobs
