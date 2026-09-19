"""Repeatable offline retrieval evaluation for the included fixture corpus."""

from __future__ import annotations

import json
from pathlib import Path

from .documents import load_corpus
from .retrieval import LocalRetriever


DEFAULT_EVALUATION = Path(__file__).resolve().parent / "data" / "evaluation.json"


def evaluate_retrieval(top_k: int = 3, path: str | Path | None = None) -> dict[str, float | int]:
    rows = json.loads(Path(path or DEFAULT_EVALUATION).read_text(encoding="utf-8"))
    retriever = LocalRetriever(load_corpus())
    hits = 0
    reciprocal_rank = 0.0
    for row in rows:
        ranked_ids = [hit.document.id for hit in retriever.search(row["query"], top_k=top_k)]
        if row["expected_document_id"] in ranked_ids:
            hits += 1
            reciprocal_rank += 1 / (ranked_ids.index(row["expected_document_id"]) + 1)
    total = len(rows)
    return {
        "cases": total,
        "top_k": top_k,
        "recall_at_k": round(hits / total, 4) if total else 0.0,
        "mrr_at_k": round(reciprocal_rank / total, 4) if total else 0.0,
    }
