"""Portable human-labelled JSONL evaluation-set support."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .evaluation import RetrievalCase, RetrievalEvaluation, evaluate_retrieval


REQUIRED_FIELDS = {"case_id", "split", "task_type", "query", "filters", "relevant_jobs", "annotation_status"}
VALID_TASK_TYPES = {"company_exact", "role_intent", "skill_retrieval", "cycle_filter", "location_filter", "negative_query", "agent_plan"}


@dataclass(frozen=True)
class LabeledCareerCase:
    case_id: str
    split: str
    task_type: str
    query: str
    filters: dict[str, Any]
    relevant_jobs: tuple[tuple[str, str], ...]
    annotation_status: str
    should_return_results: bool = True


def load_labeled_cases(path: str | Path) -> list[LabeledCareerCase]:
    """Load human-maintained JSONL and reject incomplete labels early."""
    cases: list[LabeledCareerCase] = []
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        data = json.loads(raw)
        missing = REQUIRED_FIELDS - set(data)
        if missing:
            raise ValueError(f"line {line_number}: missing {sorted(missing)}")
        if data["task_type"] not in VALID_TASK_TYPES:
            raise ValueError(f"line {line_number}: unsupported task_type {data['task_type']}")
        references = tuple((str(item["source_name"]), str(item["external_id"])) for item in data["relevant_jobs"])
        cases.append(LabeledCareerCase(str(data["case_id"]), str(data["split"]), str(data["task_type"]), str(data["query"]), dict(data["filters"]), references, str(data["annotation_status"]), bool(data.get("should_return_results", True))))
    return cases


def score_retrieval_cases(cases: Iterable[LabeledCareerCase], *, reference_to_job_id: dict[tuple[str, str], str], search: Callable[[str], Iterable[str]]) -> RetrievalEvaluation:
    """Score ready retrieval labels, resolving stable source/external IDs at runtime."""
    ready = [case for case in cases if case.annotation_status == "ready" and case.task_type != "agent_plan"]
    retrieval_cases = [
        RetrievalCase(case.query, tuple(reference_to_job_id[item] for item in case.relevant_jobs if item in reference_to_job_id))
        for case in ready if case.should_return_results and any(item in reference_to_job_id for item in case.relevant_jobs)
    ]
    return evaluate_retrieval(retrieval_cases, search)
