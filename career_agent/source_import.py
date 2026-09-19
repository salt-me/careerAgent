"""Safe import helpers for authorised CSV/JSONL JD exports.

The application does not scrape login-protected job platforms.  Instead it
validates an export supplied through an authorised API, partner integration, or
manual review, then writes an immutable JSONL batch that the corpus loader can
consume.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .scalable_corpus import CorpusValidationError, validate_and_normalise


@dataclass(frozen=True)
class ImportResult:
    accepted: int
    rejected: int
    errors: list[str]


def iter_csv_records(path: str | Path, *, source_name: str) -> Iterable[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            yield {**row, "source_name": source_name}


def validate_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], ImportResult]:
    accepted: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, record in enumerate(records, start=2):
        try:
            validate_and_normalise(record)
        except CorpusValidationError as error:
            errors.append(f"row {index}: {error}")
        else:
            accepted.append(record)
    return accepted, ImportResult(accepted=len(accepted), rejected=len(errors), errors=errors)


def write_jsonl_batch(records: Iterable[dict[str, Any]], output_path: str | Path, *, overwrite: bool = False) -> None:
    """Write a validated source batch; refusal to overwrite is the safe default."""
    destination = Path(output_path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {destination}; choose a new batch filename or pass overwrite=True")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    destination.write_text(payload, encoding="utf-8")
