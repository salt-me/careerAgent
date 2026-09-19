"""Recommended API entry point backed by the 12-record curated public JD corpus."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .curated_vector_store import CuratedJDVectorStore
from .jd_corpus import find_curated_jd, load_curated_jds
from .langgraph_flow import run_langgraph_workflow


class CuratedMatchRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=40_000)
    job_id: str = Field(min_length=1)


app = FastAPI(title="CareerAgent Curated JD Service", version="0.4.0")
store = CuratedJDVectorStore()


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "vector_store_ready": store.is_ready(), "curated_jd_count": len(load_curated_jds())}


@app.get("/api/jds")
def list_jds() -> list[dict]:
    return load_curated_jds()


@app.get("/api/jds/search")
def search_jds(query: str = Query(min_length=2, max_length=2_000), limit: int = Query(default=5, ge=1, le=10)) -> list[dict]:
    try:
        return [asdict(hit) for hit in store.search(query, limit)]
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/jds/match")
def match_jd(payload: CuratedMatchRequest) -> dict:
    try:
        job = find_curated_jd(payload.job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    result = run_langgraph_workflow(payload.resume_text, job["text"], route="interview").to_dict()
    result["public_jd"] = {key: value for key, value in job.items() if key != "text"}
    return result
