"""Resilient, auditable importer for a 10,000-record CC0 full-JD corpus.

This module deliberately samples across every structured job function offered
by the Open Jobs source.  Before filling the remaining quota, it reserves
records from at least ten distinct companies for each included function.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from .open_jobs_cc0_import import (
    CONTENT_COLUMNS,
    DEFAULT_MANIFEST,
    DEFAULT_OUTPUT,
    METADATA_COLUMNS,
    OPEN_JOBS_URL,
    ImportSummary,
    _is_metadata_candidate,
    _occupation_group,
    _raw_record,
    _text,
)
from .retrying_http_range_reader import RetryingHTTPRangeReader


def _company_key(row: dict[str, Any]) -> str:
    return _text(row["company"]).casefold()


def _candidate_key(candidate: tuple[int, int, dict[str, Any]]) -> tuple[int, int]:
    return candidate[0], candidate[1]


def _priority_candidates(
    candidates: list[tuple[int, int, dict[str, Any]]],
    eligible_groups: set[str],
    minimum: int,
) -> list[tuple[int, int, dict[str, Any]]]:
    """Reserve up to 15 companies per job function to absorb invalid JDs."""
    reserved_per_group = max(minimum + 5, minimum)
    seen_by_group: defaultdict[str, set[str]] = defaultdict(set)
    selected: list[tuple[int, int, dict[str, Any]]] = []
    for candidate in candidates:
        group = _occupation_group(candidate[2])
        company = _company_key(candidate[2])
        if group not in eligible_groups or company in seen_by_group[group]:
            continue
        if len(seen_by_group[group]) >= reserved_per_group:
            continue
        seen_by_group[group].add(company)
        selected.append(candidate)
    return selected


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
    """Build a 10k full-JD batch while retaining source provenance and coverage."""
    if target_records < 1:
        raise ValueError("target_records must be positive")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing corpus batch: {output_path}")
    if captured_at is None:
        from datetime import date

        captured_at = date.today().isoformat()

    reader = RetryingHTTPRangeReader(source_url)
    parquet = pq.ParquetFile(reader)
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    companies_by_group: defaultdict[str, set[str]] = defaultdict(set)
    groups_scanned = 0
    # A buffer avoids failing if the small number of metadata-valid entries
    # without a usable long JD are encountered in the final write phase.
    candidate_target = target_records + max(1_000, target_records // 10)
    try:
        for group_index in range(min(max_row_groups, parquet.metadata.num_row_groups)):
            rows = parquet.read_row_group(group_index, columns=METADATA_COLUMNS).to_pylist()
            groups_scanned += 1
            for row_index, row in enumerate(rows):
                if not _is_metadata_candidate(row):
                    continue
                group = _occupation_group(row)
                candidates.append((group_index, row_index, row))
                companies_by_group[group].add(_company_key(row))
            eligible_count = sum(
                1
                for _, _, row in candidates
                if len(companies_by_group[_occupation_group(row)]) >= min_companies_per_position
            )
            if eligible_count >= candidate_target:
                break

        eligible_groups = {
            group
            for group, companies in companies_by_group.items()
            if len(companies) >= min_companies_per_position
        }
        eligible_candidates = [item for item in candidates if _occupation_group(item[2]) in eligible_groups]
        if len(eligible_candidates) < candidate_target:
            raise RuntimeError(
                f"Only {len(eligible_candidates)} eligible candidates after {groups_scanned} row groups; increase max_row_groups."
            )

        priority = _priority_candidates(eligible_candidates, eligible_groups, min_companies_per_position)
        priority_keys = {_candidate_key(item) for item in priority}
        selection_order = priority + [item for item in eligible_candidates if _candidate_key(item) not in priority_keys]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".part")
        materialized_groups: dict[int, list[dict[str, Any]]] = {}
        records: list[dict[str, Any]] = []
        seen_source_urls: set[str] = set()

        def materialize(candidate: tuple[int, int, dict[str, Any]]) -> dict[str, Any] | None:
            group_index, row_index, _ = candidate
            if group_index not in materialized_groups:
                materialized_groups[group_index] = parquet.read_row_group(
                    group_index, columns=CONTENT_COLUMNS
                ).to_pylist()
            raw = _raw_record(materialized_groups[group_index][row_index], captured_at)
            if raw is None or raw["source_url"] in seen_source_urls:
                return None
            seen_source_urls.add(raw["source_url"])
            return raw

        try:
            for candidate in selection_order:
                raw = materialize(candidate)
                if raw is not None:
                    records.append(raw)
                if len(records) >= target_records:
                    break

            if len(records) < target_records:
                raise RuntimeError(f"Only {len(records)} selected rows had a usable JD; no partial corpus was retained.")

            output_companies: defaultdict[str, set[str]] = defaultdict(set)
            for record in records:
                output_companies[record["position"]].add(record["company"].casefold())
            insufficient = {
                group: len(companies)
                for group, companies in output_companies.items()
                if len(companies) < min_companies_per_position
            }
            if insufficient:
                raise RuntimeError(f"Coverage safeguard failed: {insufficient}")

            with temporary_path.open("w", encoding="utf-8", newline="\n") as stream:
                for record in records:
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            temporary_path.replace(output_path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

        manifest = {
            "provider": "open-jobs",
            "provider_repository": "https://github.com/elliottdehn/open-jobs",
            "license": "CC0-1.0",
            "source_url": source_url,
            "range_source_info": asdict(reader.info),
            "captured_at": captured_at,
            "scanned_row_groups": groups_scanned,
            "scanned_candidates": len(candidates),
            "records_written": len(records),
            "minimum_companies_per_position": min_companies_per_position,
            "company_counts_by_position": dict(
                sorted((group, len(companies)) for group, companies in output_companies.items())
            ),
            "coverage_basis": "source structured function and normalized company names",
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return ImportSummary(
            scanned_row_groups=groups_scanned,
            scanned_candidates=len(candidates),
            eligible_occupation_groups=len(eligible_groups),
            records_written=len(records),
            output_path=str(output_path),
            manifest_path=str(manifest_path),
        )
    finally:
        reader.close()

