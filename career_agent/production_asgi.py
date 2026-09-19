"""Production HTTP service for the 10k+ all-job JD corpus."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .production_corpus import load_production_job_records, production_report
from .production_search import ProductionJobSearchStore
from .universal_matching import build_universal_match


class MatchRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=40_000)
    job_id: str = Field(min_length=1)


app = FastAPI(title="CareerAgent Production All-Job JD Service", version="1.2.0")
store = ProductionJobSearchStore()


def _records_by_id() -> dict[str, dict]:
    records, _ = load_production_job_records()
    return {record["id"]: record for record in records}


@app.get("/health")
def health() -> dict:
    records, deduplication = load_production_job_records()
    report = production_report(records)
    return {"status": "ok", "vector_store_ready": store.is_ready(), "deduplication": deduplication, **report}


@app.get("/api/corpus/report")
def report() -> dict:
    records, deduplication = load_production_job_records()
    result = production_report(records)
    result["deduplication"] = deduplication
    return result


@app.get("/api/jobs/search")
def search_jobs(
    query: str = Query(min_length=2, max_length=2_000),
    limit: int = Query(default=10, ge=1, le=50),
    position: str | None = None,
    source_name: str | None = None,
) -> list[dict]:
    try:
        return [hit.to_dict() for hit in store.search(query, limit=limit, position=position, source_name=source_name)]
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/jobs/match")
def match_job(payload: MatchRequest) -> dict:
    job = _records_by_id().get(payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Public JD not found")
    return {
        "job": {key: value for key, value in job.items() if key != "text"},
        "match": build_universal_match(payload.resume_text, job).to_dict(),
    }

