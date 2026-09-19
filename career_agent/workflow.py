"""Explicit stateful workflow with traceable routing.

The interfaces map one-to-one to future LangGraph nodes: retrieve -> match/interview
-> critic. The fallback keeps this project runnable without an external dependency.
"""

from __future__ import annotations

import time
import uuid
from typing import Literal

from .critic import validate
from .documents import load_corpus
from .interview import build_interview_questions
from .matching import build_match_report
from .models import WorkflowResult
from .retrieval import LocalRetriever


class CareerWorkflow:
    def __init__(self) -> None:
        self.retriever = LocalRetriever(load_corpus())

    def run(
        self,
        resume_text: str,
        jd_text: str,
        route: Literal["match", "interview"] = "match",
    ) -> WorkflowResult:
        if not resume_text.strip() or not jd_text.strip():
            raise ValueError("resume_text 和 jd_text 均不能为空。")
        result = WorkflowResult(request_id=str(uuid.uuid4()), route=route)
        start = time.perf_counter()
        result.trace.append({"node": "input_validation", "status": "ok", "elapsed_ms": 0.0})
        match_start = time.perf_counter()
        result.match = build_match_report(resume_text, jd_text, self.retriever)
        result.trace.append(
            {"node": "match_agent", "status": "ok", "elapsed_ms": round((time.perf_counter() - match_start) * 1000, 2)}
        )
        if route == "interview":
            question_start = time.perf_counter()
            result.interview_questions = build_interview_questions(result.match)
            result.trace.append(
                {"node": "interview_agent", "status": "ok", "elapsed_ms": round((time.perf_counter() - question_start) * 1000, 2)}
            )
        critic_start = time.perf_counter()
        result.critic = validate(result.match, result.interview_questions)
        result.trace.append(
            {"node": "critic", "status": "passed" if result.critic.passed else "blocked", "elapsed_ms": round((time.perf_counter() - critic_start) * 1000, 2)}
        )
        result.trace.append({"node": "workflow", "status": "ok", "elapsed_ms": round((time.perf_counter() - start) * 1000, 2)})
        return result
