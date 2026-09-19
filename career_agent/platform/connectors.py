"""Pluggable authorised data connectors for public ATS and reviewed snapshots."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any, default: str = "") -> str:
    return re.sub(r"\s+", " ", str(value or default)).strip()


def _strip_html(value: str) -> str:
    return _text(unescape(re.sub(r"<[^>]+>", " ", value)))


def _language(text: str) -> str:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk >= 20 and cjk >= latin * 0.2:
        return "zh"
    return "en" if latin >= 20 else "unknown"


@dataclass(frozen=True)
class IncomingJob:
    source_name: str
    external_id: str
    source_url: str
    company: str
    title: str
    description: str
    location: str = "not_disclosed"
    declared_status: str = "unknown"  # open / closed / unknown
    published_at: str | None = None
    language: str = "unknown"
    declared_group: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_inferred_language(self) -> "IncomingJob":
        if self.language != "unknown":
            return self
        return IncomingJob(**{**self.__dict__, "language": _language(f"{self.title} {self.description}")})


class JobConnector(Protocol):
    name: str
    authoritative: bool

    def fetch(self) -> list[IncomingJob]: ...


class GreenhouseConnector:
    """Connector for Greenhouse's documented public job-board endpoint."""

    authoritative = True

    def __init__(
        self,
        board_token: str,
        *,
        fetch_json: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self.board_token = board_token
        self.name = f"greenhouse:{board_token}"
        self._fetch_json = fetch_json or self._http_get_json

    @staticmethod
    def _http_get_json(url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": "CareerAgent/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch(self) -> list[IncomingJob]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs?content=true"
        payload = self._fetch_json(url)
        jobs: list[IncomingJob] = []
        for item in payload.get("jobs", []):
            title = _text(item.get("title"))
            absolute_url = _text(item.get("absolute_url"))
            external_id = _text(item.get("id"))
            if not title or not absolute_url or not external_id:
                continue
            location = _text((item.get("location") or {}).get("name"), "not_disclosed")
            departments = [
                _text(value.get("name")) for value in item.get("departments", []) if _text(value.get("name"))
            ]
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=external_id,
                    source_url=absolute_url,
                    company=self.board_token,
                    title=title,
                    description=_strip_html(_text(item.get("content"))),
                    location=location,
                    declared_status="open",
                    published_at=_text(item.get("updated_at")) or None,
                    declared_group=" ".join(departments),
                    metadata={"connector": "greenhouse", "board_token": self.board_token, "departments": departments},
                ).with_inferred_language()
            )
        return jobs


class JsonlSnapshotConnector:
    """Imports an already-authorised/reviewed batch without declaring closures.

    This supports historical Chinese platform exports and licensed snapshots.
    It is intentionally non-authoritative: absence from a snapshot must never
    close a real job.
    """

    authoritative = False

    def __init__(self, name: str, paths: Iterable[Path]) -> None:
        self.name = name
        self.paths = tuple(Path(path) for path in paths)

    @staticmethod
    def _id(raw: dict[str, Any]) -> str:
        provided = _text(raw.get("source_job_id")) or _text(raw.get("id"))
        if provided:
            return provided
        digest = hashlib.sha256(_text(raw.get("source_url")).encode("utf-8")).hexdigest()[:24]
        return f"snapshot-{digest}"

    def fetch(self) -> list[IncomingJob]:
        jobs: list[IncomingJob] = []
        for path in self.paths:
            with path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    source_url = _text(raw.get("source_url"))
                    title = _text(raw.get("title"))
                    company = _text(raw.get("company"))
                    text = _text(raw.get("text"))
                    if not all((source_url, title, company, text)):
                        continue
                    jobs.append(
                        IncomingJob(
                            source_name=_text(raw.get("source_name"), self.name),
                            external_id=self._id(raw),
                            source_url=source_url,
                            company=company,
                            title=title,
                            description=text,
                            location=_text(raw.get("location"), "not_disclosed"),
                            declared_status=_text(raw.get("source_status"), "unknown").casefold(),
                            published_at=_text(raw.get("published_at")) or None,
                            language=_text(raw.get("language"), "unknown"),
                            declared_group=_text(raw.get("position")),
                            metadata={"connector": self.name, "snapshot_path": path.name, "raw_source": raw.get("source_name")},
                        ).with_inferred_language()
                    )
        return jobs


class StaticConnector:
    """Small in-memory connector used by tests and local demonstrations."""

    def __init__(self, name: str, jobs: Iterable[IncomingJob], *, authoritative: bool = True) -> None:
        self.name = name
        self.jobs = list(jobs)
        self.authoritative = authoritative

    def fetch(self) -> list[IncomingJob]:
        return list(self.jobs)

