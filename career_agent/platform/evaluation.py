"""Small deterministic evaluation harness for retrieval regression checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    relevant_job_ids: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvaluation:
    cases: int
    hit_at_1: float
    hit_at_3: float
    hit_at_10: float
    mean_reciprocal_rank: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def evaluate_retrieval(
    cases: Iterable[RetrievalCase],
    search: Callable[[str], Iterable[str]],
) -> RetrievalEvaluation:
    """Evaluate ranked IDs without depending on a network/model at test time."""
    materialized = list(cases)
    if not materialized:
        return RetrievalEvaluation(0, 0.0, 0.0, 0.0, 0.0)
    hits_1 = hits_3 = hits_10 = 0
    reciprocal_sum = 0.0
    for case in materialized:
        ranked = list(search(case.query))[:10]
        relevant = set(case.relevant_job_ids)
        positions = [index + 1 for index, job_id in enumerate(ranked) if job_id in relevant]
        if positions:
            first = positions[0]
            reciprocal_sum += 1 / first
            hits_1 += first <= 1
            hits_3 += first <= 3
            hits_10 += first <= 10
    count = len(materialized)
    return RetrievalEvaluation(
        cases=count,
        hit_at_1=round(hits_1 / count, 4),
        hit_at_3=round(hits_3 / count, 4),
        hit_at_10=round(hits_10 / count, 4),
        mean_reciprocal_rank=round(reciprocal_sum / count, 4),
    )
