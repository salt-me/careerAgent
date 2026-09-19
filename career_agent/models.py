"""Small, dependency-free domain models used by CareerAgent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MatchStatus = Literal["match", "partial", "missing_evidence"]


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str
    source: str
    category: str


@dataclass(frozen=True)
class Citation:
    document_id: str
    title: str
    source: str
    excerpt: str


@dataclass(frozen=True)
class RetrievalHit:
    document: Document
    score: float
    matched_terms: list[str]


@dataclass(frozen=True)
class MatchDimension:
    skill: str
    required: bool
    status: MatchStatus
    resume_evidence: str | None
    jd_evidence: str
    recommendation: str


@dataclass(frozen=True)
class MatchReport:
    score: float
    level: Literal["strong", "potential", "needs_preparation"]
    dimensions: list[MatchDimension]
    citations: list[Citation]
    summary: str


@dataclass(frozen=True)
class InterviewQuestion:
    skill: str
    question: str
    intent: str
    preparation_hint: str
    citations: list[Citation]


@dataclass(frozen=True)
class CriticReport:
    passed: bool
    issues: list[str]
    checks: dict[str, bool]


@dataclass
class WorkflowResult:
    request_id: str
    route: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    match: MatchReport | None = None
    interview_questions: list[InterviewQuestion] = field(default_factory=list)
    critic: CriticReport | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
