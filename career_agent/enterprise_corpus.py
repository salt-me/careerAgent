"""Production corpus augmented with net-new official company ATS job records."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from .large_corpus import _normalise_open_jobs, _stable_id, iter_jsonl, large_coverage_report
from .production_corpus import load_production_job_records
from .scalable_corpus import canonical_company


OFFICIAL_ATS_BATCH = Path(__file__).resolve().parent / "data" / "licensed_sources" / "official_ats_100plus_companies.jsonl"


def _normalise_official_ats_record(raw: dict) -> dict:
    record = _normalise_open_jobs(raw)
    source_name = "official_ats_cc0"
    record["id"] = _stable_id(source_name, str(raw["source_job_id"]), record["source_url"])
    record["source_name"] = source_name
    record["source_provider"] = "company_official_ats"
    record["source_license"] = "CC0-1.0"
    record["source_type"] = "direct_company_ats_url"
    record["source_status"] = "unknown"
    record["live_vacancy"] = False
    record["ats_host"] = urlparse(record["source_url"]).netloc.casefold()
    return record


def load_enterprise_job_records(*, official_paths: Iterable[Path] | None = None) -> tuple[list[dict], dict[str, int]]:
    """Merge the base production corpus with exact-identity official ATS records."""
    paths = list(official_paths) if official_paths is not None else [OFFICIAL_ATS_BATCH]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Official ATS corpus batch is missing: {', '.join(map(str, missing))}")
    records, base_deduplication = load_production_job_records()
    records = list(records)
    for path in paths:
        records.extend(_normalise_official_ats_record(raw) for raw in iter_jsonl(path))
    identities: set[tuple[str, str]] = set()
    kept: list[dict] = []
    duplicates = 0
    for record in records:
        identity = (record["source_name"], record["source_job_id"] or record["source_url"])
        if identity in identities:
            duplicates += 1
            continue
        identities.add(identity)
        kept.append(record)
    return kept, {**base_deduplication, "official_ats_exact_source_duplicates_removed": duplicates}


def enterprise_report(records: Iterable[dict]) -> dict:
    records = list(records)
    report = large_coverage_report(records)
    official = [record for record in records if record["source_name"] == "official_ats_cc0"]
    report["official_enterprise_summary"] = {
        "records": len(official),
        "net_new_companies": len({canonical_company(record["company"]) for record in official}),
        "direct_ats_host_count": len({record["ats_host"] for record in official}),
        "direct_ats_host_distribution": dict(Counter(record["ats_host"] for record in official).most_common()),
        "source_status_policy": "unknown: original ATS URLs must be checked before applying",
    }
    return report

