from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.platform.career_portal_next_app import create_career_portal_next_app


class Hit:
    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.score = 0.9


class StubVectorStore:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id

    def search(self, *_args, **_kwargs):
        return [Hit(self.job_id)]


def test_next_portal_supports_search_detail_match_and_local_tracking(platform_components) -> None:
    job = platform_components.repository.jobs_for_index()[0]
    platform_components.vector_store = StubVectorStore(job.id)  # type: ignore[assignment]
    app = create_career_portal_next_app(platform_components)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        search = client.get("/api/career/search", params={"query": "Python", "scope": "live"})
        assert search.status_code == 200
        assert search.json()["items"][0]["id"] == job.id
        assert client.get(f"/api/career/jobs/{job.id}").status_code == 200
        match = client.post("/api/career/match", json={"job_id": job.id, "resume_text": "Python SQL"})
        assert match.status_code == 200
        assert "boundary_notice" in match.json()["match"]
        assert client.post("/api/career/bookmarks", json={"job_id": job.id, "note": "priority"}).status_code == 200
        assert client.get("/api/career/bookmarks").json()[0]["job_id"] == job.id
        assert client.post("/api/career/applications", json={"job_id": job.id, "stage": "applied"}).status_code == 200
        assert client.get("/api/career/applications").json()[0]["stage"] == "applied"
        assert client.post("/api/career/subscriptions", json={"name": "Python campus", "query": "Python"}).status_code == 200
        assert client.get("/api/career/subscriptions").json()[0]["query"] == "Python"


def test_next_portal_rejects_invalid_application_stage(platform_components) -> None:
    job = platform_components.repository.jobs_for_index()[0]
    app = create_career_portal_next_app(platform_components)
    with TestClient(app) as client:
        response = client.post("/api/career/applications", json={"job_id": job.id, "stage": "magic"})
    assert response.status_code == 422
