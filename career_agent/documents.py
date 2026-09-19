"""Corpus loading and document helpers."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Document


DEFAULT_CORPUS = Path(__file__).resolve().parent / "data" / "knowledge_base.json"


def load_corpus(path: str | Path | None = None) -> list[Document]:
    corpus_path = Path(path) if path else DEFAULT_CORPUS
    rows = json.loads(corpus_path.read_text(encoding="utf-8"))
    return [Document(**row) for row in rows]


def input_document(document_id: str, title: str, text: str) -> Document:
    return Document(
        id=document_id,
        title=title,
        text=text,
        source=f"input://{document_id}",
        category="user_input",
    )
