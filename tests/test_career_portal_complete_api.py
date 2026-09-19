from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.platform.career_portal_complete_app import create_complete_career_portal_app


def test_complete_portal_parses_resume_and_previews_subscription(platform_components) -> None:
    job = platform_components.repository.jobs_for_index()[0]
    app = create_complete_career_portal_app(platform_components)
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert 'id="resumeFile"' in root.text
        assert "严格匹配" in root.text
        assert "\\u4e25" not in root.text
        parsed = client.post("/api/career/resume/parse?filename=resume.txt", content="项目经历 Python SQL Docker".encode(), headers={"content-type": "text/plain"})
        assert parsed.status_code == 200
        assert "Python" in parsed.json()["skills"]
        subscription = client.post("/api/career/subscriptions", json={"name": "campus", "query": "Python", "filters": {"scope": "live"}}).json()
        preview = client.get(f"/api/career/subscriptions/{subscription['id']}/preview")
        assert preview.status_code == 200
        assert preview.json()["subscription_id"] == subscription["id"]
