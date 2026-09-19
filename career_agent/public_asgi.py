"""FastAPI endpoints for indexed public JDs and evidence-grounded matching."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .langgraph_flow import run_langgraph_workflow
from .public_jds import find_public_jd, load_public_jds
from .vector_retrieval import PublicJDVectorStore


class PublicMatchRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=40_000)
    job_id: str = Field(min_length=1)


app = FastAPI(title="CareerAgent Public JD Service", version="0.3.0")
store = PublicJDVectorStore()


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "vector_store_ready": store.is_ready(), "public_jd_count": len(load_public_jds())}


@app.post("/api/public-jds/rebuild")
def rebuild() -> dict[str, str | int]:
    try:
        return store.rebuild()
    except Exception as error:  # model downloads and local file errors should reach the operator
        raise HTTPException(status_code=503, detail=f"向量库创建失败：{error}") from error


@app.get("/api/public-jds")
def list_public_jds() -> list[dict]:
    return load_public_jds()


@app.get("/api/public-jds/search")
def search_public_jds(query: str = Query(min_length=2, max_length=2_000), limit: int = Query(default=3, ge=1, le=10)) -> list[dict]:
    try:
        return [asdict(hit) for hit in store.search(query, limit)]
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/public-jds/match")
def match_public_jd(payload: PublicMatchRequest) -> dict:
    try:
        job = find_public_jd(payload.job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    result = run_langgraph_workflow(payload.resume_text, job["text"], route="interview").to_dict()
    result["public_jd"] = {key: value for key, value in job.items() if key != "text"}
    return result
