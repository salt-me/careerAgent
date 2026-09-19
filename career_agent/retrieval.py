"""Dependency-free sparse retrieval plus a transparent skill-overlap reranker."""

from __future__ import annotations

import math
import re
from collections import Counter

from .catalog import extract_skills
from .models import Citation, Document, RetrievalHit


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    ascii_terms = re.findall(r"[a-z][a-z0-9+#.-]{1,}", lowered)
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    bigrams = [chinese[index : index + 2] for index in range(max(0, len(chinese) - 1))]
    return ascii_terms + bigrams


class LocalRetriever:
    """A reproducible retrieval baseline that needs neither network nor a model API."""

    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self._doc_terms = {doc.id: Counter(tokenize(doc.text)) for doc in documents}
        self._doc_skills = {doc.id: extract_skills(doc.text) for doc in documents}
        document_frequency: Counter[str] = Counter()
        for terms in self._doc_terms.values():
            document_frequency.update(terms.keys())
        self._idf = {
            term: math.log((1 + len(documents)) / (1 + frequency)) + 1
            for term, frequency in document_frequency.items()
        }

    def search(self, query: str, top_k: int = 4) -> list[RetrievalHit]:
        query_terms = Counter(tokenize(query))
        query_skills = extract_skills(query)
        if not query_terms and not query_skills:
            return []
        hits: list[RetrievalHit] = []
        for document in self.documents:
            terms = self._doc_terms[document.id]
            lexical = sum(
                min(query_tf, terms.get(term, 0)) * self._idf.get(term, 0.0)
                for term, query_tf in query_terms.items()
            )
            overlap = query_skills & self._doc_skills[document.id]
            # Reranking prioritises documents that explicitly cover requested skills.
            score = lexical + 2.5 * len(overlap)
            if score:
                matched = sorted(overlap) + sorted(
                    term for term in query_terms if term in terms and term not in overlap
                )[:5]
                hits.append(RetrievalHit(document=document, score=round(score, 4), matched_terms=matched))
        return sorted(hits, key=lambda hit: (-hit.score, hit.document.id))[:top_k]


def citation_from_hit(hit: RetrievalHit, query: str) -> Citation:
    query_skills = extract_skills(query)
    candidates = re.split(r"[\n。！？!?；;]+", hit.document.text)
    excerpt = next(
        (
            candidate.strip()
            for candidate in candidates
            if candidate.strip() and query_skills & extract_skills(candidate)
        ),
        hit.document.text.strip(),
    )
    return Citation(
        document_id=hit.document.id,
        title=hit.document.title,
        source=hit.document.source,
        excerpt=excerpt[:280],
    )
