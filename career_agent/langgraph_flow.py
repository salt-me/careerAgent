"""LangGraph implementation of the CareerAgent workflow.

The business rules stay deterministic and auditable; LangGraph owns routing and
state transitions so the same graph can later gain streaming, persistence or HITL.
"""

from __future__ import annotations

import time
import uuid
from typing import Literal

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .critic import validate
from .documents import load_corpus
from .interview import build_interview_questions
from .matching import build_match_report
from .models import CriticReport, InterviewQuestion, MatchReport, WorkflowResult
from .retrieval import LocalRetriever


class CareerState(TypedDict, total=False):
    request_id: str
    route: Literal["match", "interview"]
    resume_text: str
    jd_text: str
    match: MatchReport
    interview_questions: list[InterviewQuestion]
    critic: CriticReport
    trace: list[dict[str, str | float]]


_retriever = LocalRetriever(load_corpus())


def _timed_trace(state: CareerState, node: str, started_at: float, status: str = "ok") -> list[dict[str, str | float]]:
    return [
        *state.get("trace", []),
        {"node": node, "status": status, "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2)},
    ]


def validate_input(state: CareerState) -> dict[str, object]:
    started_at = time.perf_counter()
    if not state["resume_text"].strip() or not state["jd_text"].strip():
        raise ValueError("resume_text 和 jd_text 均不能为空。")
    return {"trace": _timed_trace(state, "input_validation", started_at)}


def match_agent(state: CareerState) -> dict[str, object]:
    started_at = time.perf_counter()
    report = build_match_report(state["resume_text"], state["jd_text"], _retriever)
    return {"match": report, "trace": _timed_trace(state, "match_agent", started_at)}


def route_after_match(state: CareerState) -> Literal["interview_agent", "critic"]:
    return "interview_agent" if state["route"] == "interview" else "critic"


def interview_agent(state: CareerState) -> dict[str, object]:
    started_at = time.perf_counter()
    questions = build_interview_questions(state["match"])
    return {"interview_questions": questions, "trace": _timed_trace(state, "interview_agent", started_at)}


def critic(state: CareerState) -> dict[str, object]:
    started_at = time.perf_counter()
    report = validate(state["match"], state.get("interview_questions", []))
    return {
        "critic": report,
        "trace": _timed_trace(state, "critic", started_at, "passed" if report.passed else "blocked"),
    }


builder = StateGraph(CareerState)
builder.add_node("input_validation", validate_input)
builder.add_node("match_agent", match_agent)
builder.add_node("interview_agent", interview_agent)
builder.add_node("critic", critic)
builder.add_edge(START, "input_validation")
builder.add_edge("input_validation", "match_agent")
builder.add_conditional_edges("match_agent", route_after_match, ["interview_agent", "critic"])
builder.add_edge("interview_agent", "critic")
builder.add_edge("critic", END)
career_graph = builder.compile()


def run_langgraph_workflow(
    resume_text: str,
    jd_text: str,
    route: Literal["match", "interview"] = "match",
) -> WorkflowResult:
    """Run the graph and adapt its typed state to the public response model."""
    started_at = time.perf_counter()
    state = career_graph.invoke(
        {
            "request_id": str(uuid.uuid4()),
            "route": route,
            "resume_text": resume_text,
            "jd_text": jd_text,
            "interview_questions": [],
            "trace": [],
        }
    )
    trace = [*state["trace"], {"node": "workflow", "status": "ok", "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2)}]
    return WorkflowResult(
        request_id=state["request_id"],
        route=state["route"],
        trace=trace,
        match=state["match"],
        interview_questions=state.get("interview_questions", []),
        critic=state["critic"],
    )
