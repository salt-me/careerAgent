"""FastAPI service for the LangGraph CareerAgent workflow."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .api import PAGE
from .langgraph_flow import run_langgraph_workflow


class AnalysisRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=40_000, description="脱敏后的简历文本")
    jd_text: str = Field(min_length=1, max_length=40_000, description="岗位 JD 文本")


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=1)
    helpful: bool
    note: str = Field(default="", max_length=500)


app = FastAPI(
    title="CareerAgent",
    version="0.2.0",
    description="Evidence-grounded job matching and interview preparation.",
)
_feedback: list[FeedbackRequest] = []


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    return PAGE


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "langgraph"}


def _analyze(payload: AnalysisRequest, route: str) -> dict:
    try:
        return run_langgraph_workflow(payload.resume_text, payload.jd_text, route=route).to_dict()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/match")
def match(payload: AnalysisRequest) -> dict:
    return _analyze(payload, "match")


@app.post("/api/interview")
def interview(payload: AnalysisRequest) -> dict:
    return _analyze(payload, "interview")


@app.post("/api/feedback", status_code=202)
def feedback(payload: FeedbackRequest) -> dict[str, int | str]:
    """Accept bounded in-memory feedback; persistence is deliberately opt-in."""
    _feedback.append(payload)
    return {"status": "accepted", "received": len(_feedback)}
