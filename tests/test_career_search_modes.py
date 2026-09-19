from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.platform.career_portal_complete_app import create_complete_career_portal_app


class _Hit:
    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.score = 0.8


class _UnrelatedSemanticStore:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id

    def search(self, *_args, **_kwargs):
        return [_Hit(self.job_id)]


def test_strict_search_never_silently_returns_unrelated_semantic_results(platform_components) -> None:
    job = platform_components.repository.jobs_for_index()[0]
    platform_components.vector_store = _UnrelatedSemanticStore(job.id)  # type: ignore[assignment]
    app = create_complete_career_portal_app(platform_components)
    with TestClient(app) as client:
        strict = client.get("/api/career/search", params={"query": "Huawei", "scope": "live"}).json()
        expanded = client.get(
            "/api/career/search",
            params={"query": "Huawei", "scope": "live", "expand_semantic": "true"},
        ).json()

    assert strict["match_mode"] == "no_exact_match"
    assert strict["items"] == []
    assert strict["all_results"] is True
    assert expanded["match_mode"] == "semantic_expansion"
    assert expanded["items"][0]["id"] == job.id
    assert expanded["all_results"] is False
