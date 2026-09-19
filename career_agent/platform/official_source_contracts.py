"""Declarative, audited connectors for public official JSON job feeds.

The contract deliberately requires an explicit full-enumeration confirmation
before a feed can close/archival records.  This supports adding new official
sources without hard-coding a fragile, site-specific scraper.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .connectors import IncomingJob, _strip_html, _text


JsonFetcher = Callable[[str], Any]


def _get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "CareerAgent/1.0 (+official-public-job-feed)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _at_path(payload: Any, path: str) -> list[dict[str, Any]]:
    current = payload
    for key in filter(None, path.split(".")):
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return [item for item in current if isinstance(item, dict)] if isinstance(current, list) else []


class OfficialJsonContractConnector:
    """Maps a reviewed public JSON feed into the canonical incoming-job shape."""

    def __init__(self, contract: dict[str, Any], *, fetch_json: JsonFetcher | None = None) -> None:
        required = ("id", "company", "feed_url", "field_map")
        if any(not _text(contract.get(key)) and key != "field_map" for key in required):
            raise ValueError("official JSON contract requires id, company, feed_url and field_map")
        mapping = contract["field_map"]
        if not isinstance(mapping, dict) or any(key not in mapping for key in ("external_id", "title", "source_url")):
            raise ValueError("field_map must map external_id, title and source_url")
        self.contract = contract
        self.name = f"official-json:{_text(contract['id'])}"
        self.authoritative = bool(contract.get("authoritative")) and bool(contract.get("full_enumeration_verified"))
        self._fetch_json = fetch_json or _get_json

    def fetch(self) -> list[IncomingJob]:
        payload = self._fetch_json(_text(self.contract["feed_url"]))
        fields = self.contract["field_map"]
        jobs: list[IncomingJob] = []
        for raw in _at_path(payload, _text(self.contract.get("items_path"), "jobs")):
            def field(name: str, default: str = "") -> str:
                return _text(raw.get(_text(fields.get(name))), default)
            external_id, title, source_url = field("external_id"), field("title"), field("source_url")
            if not all((external_id, title, source_url)):
                continue
            description = field("description")
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=external_id,
                    source_url=source_url,
                    company=_text(self.contract["company"]),
                    title=title,
                    description=_strip_html(description) or title,
                    location=field("location", "not_disclosed"),
                    declared_status=field("status", "open").casefold(),
                    published_at=field("published_at") or None,
                    language=field("language", "unknown"),
                    declared_group=field("group"),
                    metadata={
                        "connector": "official_json_contract",
                        "contract_id": self.contract["id"],
                        "authoritative_contract": self.authoritative,
                        "feed_url": self.contract["feed_url"],
                    },
                ).with_inferred_language()
            )
        return jobs


def configured_official_json_contracts(path: Path | None = None) -> list[OfficialJsonContractConnector]:
    configured = path or (Path(os.environ["CAREER_AGENT_OFFICIAL_SOURCE_CONTRACT_PATH"]) if os.getenv("CAREER_AGENT_OFFICIAL_SOURCE_CONTRACT_PATH") else None)
    if not configured:
        return []
    data = json.loads(configured.read_text(encoding="utf-8"))
    contracts = data.get("sources", data) if isinstance(data, dict) else data
    if not isinstance(contracts, list):
        raise ValueError("official source contract file must contain a sources list")
    return [OfficialJsonContractConnector(contract) for contract in contracts if isinstance(contract, dict) and contract.get("enabled")]
