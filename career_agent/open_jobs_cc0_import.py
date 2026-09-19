"""Bounded importer for the CC0 Open Jobs Parquet dataset.

The upstream dataset is published under CC0 and provides original ATS URLs,
company names, titles, full job descriptions and a structured function field.
This importer uses HTTP range reads and writes only a vetted 10,000-row subset.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from .http_range_reader import HTTPRangeReader


OPEN_JOBS_URL = "https://download.jobscream.com/open-jobs.parquet"
LICENSED_SOURCE_DIR = Path(__file__).resolve().parent / "data" / "licensed_sources"
DEFAULT_OUTPUT = LICENSED_SOURCE_DIR / "open_jobs_cc0_10000.jsonl"
DEFAULT_MANIFEST = LICENSED_SOURCE_DIR / "open_jobs_cc0_10000.manifest.json"
METADATA_COLUMNS = ("id", "ats", "company", "title", "location", "url", "function", "sub_function", "employment_type", "posted_at")
CONTENT_COLUMNS = (*METADATA_COLUMNS, "jd_markdown")


@dataclass(frozen=True)
class ImportSummary:
    scanned_row_groups: int
    scanned_candidates: int
    eligible_occupation_groups: int
    records_written: int
    output_path: str
    manifest_path: str


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _occupation_group(row: dict[str, Any]) -> str:
    """Use the source's structured function, not an invented title taxonomy."""
    function = _text(row.get("function")).casefold()
    return function if function and function not in {"unknown", "none", "null"} else "other"


def _is_metadata_candidate(row: dict[str, Any]) -> bool:
    return all(_text(row.get(field)) for field in ("id", "company", "title", "url")) and _occupation_group(row) != "other"


def _raw_record(row: dict[str, Any], captured_at: str) -> dict[str, Any] | None:
    text = _text(row.get("jd_markdown"))
    if len(text) < 40:
        return None
    return {
        "source_name": "open_jobs_cc0",
        "source_url": _text(row["url"]),
        "source_job_id": _text(row["id"]),
        "source_status": "unknown",
        "source_provider": "open-jobs",
        "source_license": "CC0-1.0",
        "source_ats": _text(row.get("ats")),
        "title": _text(row["title"]),
        "company": _text(row["company"]),
        "position": _occupation_group(row),
        "job_family": _occupation_group(row),
        "location": _text(row.get("location")) or "not_disclosed",
        "experience": "not_disclosed",
        "employment_type": _text(row.get("employment_type")) or "not_disclosed",
        "published_at": _text(row.get("posted_at")) or "not_disclosed",
        "captured_at": captured_at,
        "text": text,
        "source_note": "Open Jobs CC0 snapshot; original ATS application URL retained. Check the source URL before applying.",
    }


def import_subset(
    *,
    target_records: int = 10_000,
    min_companies_per_position: int = 10,
    max_row_groups: int = 12,
    source_url: str = OPEN_JOBS_URL,
    output_path: Path = DEFAULT_OUTPUT,
    manifest_path: Path = DEFAULT_MANIFEST,
    captured_at: str | None = None,
    overwrite: bool = False,
) -> ImportSummary:
    """Create an auditable bounded subset whose every occupation group has 10 companies."""
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing corpus batch: {output_path}")
    captured_at = captured_at or date.today().isoformat()
    reader = HTTPRangeReader(source_url)
    parquet = pq.ParquetFile(reader)
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    by_group: defaultdict[str, set[str]] = defaultdict(set)
    groups_scanned = 0
    try:
        for group_index in range(min(max_row_groups, parquet.metadata.num_row_groups)):
            rows = parquet.read_row_group(group_index, columns=METADATA_COLUMNS).to_pylist()
            groups_scanned += 1
            for row_index, row in enumerate(rows):
                if not _is_metadata_candidate(row):
                    continue
                group = _occupation_group(row)
                company = _text(row["company"]).casefold()
                candidates.append((group_index, row_index, row))
                by_group[group].add(company)
            eligible_count = sum(1 for _, _, row in candidates if len(by_group[_occupation_group(row)]) >= min_companies_per_position)
            if eligible_count >= target_records:
                break

        eligible_groups = {
            group for group, companies in by_group.items() if len(companies) >= min_companies_per_position
        }
        selected = [candidate for candidate in candidates if _occupation_group(candidate[2]) in eligible_groups][:target_records]
        if len(selected) < target_records:
            raise RuntimeError(
                f"Only {len(selected)} candidates from eligible occupation groups found after {groups_scanned} row groups; increase max_row_groups."
            )

        selected_offsets: defaultdict[int, set[int]] = defaultdict(set)
        for group_index, row_index, _ in selected:
            selected_offsets[group_index].add(row_index)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".part")
        written = 0
        with temporary_path.open("w", encoding="utf-8", newline="\n") as stream:
            for group_index in sorted(selected_offsets):
                rows = parquet.read_row_group(group_index, columns=CONTENT_COLUMNS).to_pylist()
                for row_index in sorted(selected_offsets[group_index]):
                    raw = _raw_record(rows[row_index], captured_at)
                    if raw is None:
                        continue
                    stream.write(json.dumps(raw, ensure_ascii=False) + "\n")
                    written += 1
        if written < target_records:
            temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"Only {written} selected rows had a usable JD; no partial corpus was retained.")
        temporary_path.replace(output_path)
        manifest = {
            "provider": "open-jobs",
            "provider_repository": "https://github.com/elliottdehn/open-jobs",
            "license": "CC0-1.0",
            "source_url": source_url,
            "range_source_info": {"size": reader.info.size, "etag": reader.info.etag, "last_modified": reader.info.last_modified},
            "captured_at": captured_at,
            "scanned_row_groups": groups_scanned,
            "scanned_candidates": len(candidates),
            "records_written": written,
            "min_companies_per_occupation_group": min_companies_per_position,
            "eligible_occupation_groups": sorted(eligible_groups),
            "company_counts_by_occupation_group": dict(sorted((group, len(companies)) for group, companies in by_group.items() if group in eligible_groups)),
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return ImportSummary(
            scanned_row_groups=groups_scanned,
            scanned_candidates=len(candidates),
            eligible_occupation_groups=len(eligible_groups),
            records_written=written,
            output_path=str(output_path),
            manifest_path=str(manifest_path),
        )
    finally:
        reader.close()
