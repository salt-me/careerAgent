"""FastAPI service for the universal job matching mode."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .universal_corpus import corpus_summary, filter_records, find_universal_record, load_universal_records
from .universal_matching import build_universal_match
from .universal_vector_store import UniversalVectorStore


class UniversalMatchRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=40_000)
    record_id: str = Field(min_length=1)


app = FastAPI(title="CareerAgent Universal Job Service", version="0.5.0")
store = UniversalVectorStore()


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "vector_store_ready": store.is_ready(), **corpus_summary()}


@app.get("/api/catalog/summary")
def catalog_summary() -> dict:
    return corpus_summary()


@app.get("/api/records")
def list_records(
    job_family: str | None = None,
    artifact_type: str | None = Query(default=None, pattern="^(public_jd|job_family_profile)$"),
    actionable_only: bool = False,
) -> list[dict]:
    return filter_records(
        load_universal_records(),
        job_family=job_family,
        artifact_type=artifact_type,
        actionable_only=actionable_only,
    )


@app.get("/api/records/search")
def search_records(
    query: str = Query(min_length=2, max_length=2_000),
    limit: int = Query(default=5, ge=1, le=10),
    job_family: str | None = None,
    artifact_type: str | None = Query(default=None, pattern="^(public_jd|job_family_profile)$"),
    actionable_only: bool = False,
) -> list[dict]:
    try:
        return [
            hit.to_dict()
            for hit in store.search(
                query,
                limit=limit,
                job_family=job_family,
                artifact_type=artifact_type,
                actionable_only=actionable_only,
            )
        ]
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/match")
def match_record(payload: UniversalMatchRequest) -> dict:
    try:
        record = find_universal_record(payload.record_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {
        "record": {key: value for key, value in record.items() if key != "text"},
        "match": build_universal_match(payload.resume_text, record).to_dict(),
    }
