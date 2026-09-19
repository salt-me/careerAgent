"""Production API for multilingual retrieval over the verified 10k corpus."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .multilingual_all_job_search import MultilingualAllJobSearchStore
from .universal_matching import build_universal_match
from .verified_all_job_corpus import large_coverage_report, load_verified_all_job_records


class MatchRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=40_000)
    job_id: str = Field(min_length=1)


app = FastAPI(title="CareerAgent Multilingual All-Job JD Service", version="1.1.0")
store = MultilingualAllJobSearchStore()


def _records_by_id() -> dict[str, dict]:
    records, _ = load_verified_all_job_records()
    return {record["id"]: record for record in records}


@app.get("/health")
def health() -> dict:
    records, deduplication = load_verified_all_job_records()
    report = large_coverage_report(records)
    return {"status": "ok", "vector_store_ready": store.is_ready(), "deduplication": deduplication, **report}


@app.get("/api/corpus/report")
def report() -> dict:
    records, deduplication = load_verified_all_job_records()
    result = large_coverage_report(records)
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

