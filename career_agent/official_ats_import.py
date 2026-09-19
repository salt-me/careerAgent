"""Bounded importer for direct company-ATS JD records in the CC0 Open Jobs snapshot.

The source dataset retains original application URLs.  This importer selects a
single later Parquet row group whose companies are absent from the current
production corpus, and enforces a minimum number of *new* companies before any
JSONL batch is retained.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pyarrow.parquet as pq

from .open_jobs_cc0_import import (
    CONTENT_COLUMNS,
    METADATA_COLUMNS,
    OPEN_JOBS_URL,
    _is_metadata_candidate,
    _occupation_group,
    _raw_record,
    _text,
)
from .production_corpus import load_production_job_records
from .retrying_http_range_reader import RetryingHTTPRangeReader
from .scalable_corpus import canonical_company


DEFAULT_ROW_GROUP = 3
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "licensed_sources" / "official_ats_100plus_companies.jsonl"
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "data" / "licensed_sources" / "official_ats_100plus_companies.manifest.json"

# These are recognised public company hiring-system hosts.  The original job
# URL is always retained, so a caller can inspect and independently verify it.
OFFICIAL_ATS_HOST_MARKERS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "recruitee.com",
    "pinpointhq.com",
    "hire.trakstar.com",
    "crelate.com",
    "personio.",
    "breezy.hr",
    "jobvite.com",
    "smartrecruiters.com",
)


def is_direct_ats_url(url: str) -> bool:
    host = urlparse(url).netloc.casefold()
    return any(marker in host for marker in OFFICIAL_ATS_HOST_MARKERS)


def _candidate_company_key(row: dict[str, Any]) -> str:
    return canonical_company(_text(row.get("company")))


def select_new_company_candidates(
    rows: list[dict[str, Any]], *, known_companies: set[str], min_new_companies: int
) -> tuple[list[int], set[str]]:
    """Keep all direct-ATS postings from companies new to the production corpus."""
    selected_indices: list[int] = []
    companies: set[str] = set()
    for index, row in enumerate(rows):
        key = _candidate_company_key(row)
        if not _is_metadata_candidate(row) or not key or key in known_companies:
            continue
        if not is_direct_ats_url(_text(row.get("url"))):
            continue
        selected_indices.append(index)
        companies.add(key)
    if len(companies) < min_new_companies:
        raise RuntimeError(f"Only {len(companies)} net-new companies found; required {min_new_companies}.")
    return selected_indices, companies


@dataclass(frozen=True)
class OfficialAtsImportSummary:
    row_group: int
    metadata_candidates: int
    selected_records: int
    records_written: int
    new_companies: int
    output_path: str
    manifest_path: str


def import_new_company_row_group(
    *,
    row_group: int = DEFAULT_ROW_GROUP,
    min_new_companies: int = 100,
    output_path: Path = DEFAULT_OUTPUT,
    manifest_path: Path = DEFAULT_MANIFEST,
    captured_at: str | None = None,
    overwrite: bool = False,
) -> OfficialAtsImportSummary:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing source batch: {output_path}")
    if row_group < 0:
        raise ValueError("row_group must be non-negative")
    captured_at = captured_at or date.today().isoformat()
    existing, _ = load_production_job_records()
    known_companies = {record["company_key"] for record in existing}

    reader = RetryingHTTPRangeReader(OPEN_JOBS_URL)
    parquet = pq.ParquetFile(reader)
    try:
        if row_group >= parquet.metadata.num_row_groups:
            raise ValueError(f"row_group {row_group} is outside this source snapshot")
        metadata_rows = parquet.read_row_group(row_group, columns=METADATA_COLUMNS).to_pylist()
        selected_indices, new_companies = select_new_company_candidates(
            metadata_rows, known_companies=known_companies, min_new_companies=min_new_companies
        )
        content_rows = parquet.read_row_group(row_group, columns=CONTENT_COLUMNS).to_pylist()
        records: list[dict[str, Any]] = []
        for index in selected_indices:
            raw = _raw_record(content_rows[index], captured_at)
            if raw is None:
                continue
            raw["source_name"] = "official_ats_cc0"
            raw["source_provider"] = "company_official_ats"
            raw["source_license"] = "CC0-1.0"
            raw["source_type"] = "direct_company_ats_url"
            records.append(raw)
        actual_companies = {canonical_company(record["company"]) for record in records}
        if len(actual_companies) < min_new_companies:
            raise RuntimeError(
                f"Only {len(actual_companies)} new companies had usable JD content; required {min_new_companies}."
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".part")
        try:
            temporary.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
            temporary.replace(output_path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        host_distribution = Counter(urlparse(record["source_url"]).netloc.casefold() for record in records)
        manifest = {
            "provider": "open-jobs",
            "provider_repository": "https://github.com/elliottdehn/open-jobs",
            "license": "CC0-1.0",
            "source_url": OPEN_JOBS_URL,
            "selection": {
                "row_group": row_group,
                "excludes_existing_production_companies": True,
                "minimum_new_companies": min_new_companies,
                "direct_ats_host_markers": list(OFFICIAL_ATS_HOST_MARKERS),
            },
            "captured_at": captured_at,
            "metadata_candidates": sum(1 for row in metadata_rows if _is_metadata_candidate(row)),
            "selected_records": len(selected_indices),
            "records_written": len(records),
            "new_companies": len(actual_companies),
            "direct_ats_host_distribution": dict(sorted(host_distribution.items())),
            "range_source_info": asdict(reader.info),
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return OfficialAtsImportSummary(
            row_group=row_group,
            metadata_candidates=manifest["metadata_candidates"],
            selected_records=len(selected_indices),
            records_written=len(records),
            new_companies=len(actual_companies),
            output_path=str(output_path),
            manifest_path=str(manifest_path),
        )
    finally:
        reader.close()

