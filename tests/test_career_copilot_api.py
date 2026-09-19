from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.platform.career_portal_complete_app import create_complete_career_portal_app
from career_agent.platform.notifications import SmtpSettings, SubscriptionNotifier
from career_agent.platform.workspace import CareerWorkspace


def test_complete_portal_profiles_grounded_plan_and_safe_delivery(platform_components, monkeypatch) -> None:
    for name in (
        "CAREER_AGENT_SMTP_HOST",
        "CAREER_AGENT_SMTP_PORT",
        "CAREER_AGENT_SMTP_USERNAME",
        "CAREER_AGENT_SMTP_PASSWORD",
        "CAREER_AGENT_SMTP_FROM",
    ):
        monkeypatch.delenv(name, raising=False)

    job = platform_components.repository.jobs_for_index()[0]
    app = create_complete_career_portal_app(platform_components)
    alpha = {"x-career-profile": "student-alpha"}
    beta = {"x-career-profile": "student-beta"}
    with TestClient(app) as client:
        assert 'id="copilotRun"' in client.get("/").text

        profile = client.put(
            "/api/career/profile",
            headers=alpha,
            json={
                "display_name": "Student",
                "email": "student@example.test",
                "target_roles": ["Python engineer"],
                "target_locations": ["Beijing"],
                "campus_cycle": "2027_autumn",
                "employment_kind": "campus",
            },
        )
        assert profile.status_code == 200
        assert profile.json()["email"] == "student@example.test"
        assert client.get("/api/career/profile", headers=beta).json()["email"] == ""
        assert client.get("/api/career/profile", headers={"x-career-profile": "bad key"}).status_code == 422

        freshness = client.get("/api/career/freshness")
        assert freshness.status_code == 200
        assert freshness.json()["open_jobs"] == 1

        plan = client.post(
            "/api/career/copilot/plan",
            headers=alpha,
            json={"target_role": "Python", "resume_text": "Python SQL", "scope": "live"},
        )
        assert plan.status_code == 200
        result = plan.json()["plan"]
        assert result["mode"] == "grounded_career_copilot"
        assert result["citations"][0]["job_id"] == job.id
        assert result["citations"][0]["source_url"] == job.source_url
        assert result["boundary"]

        subscription = client.post(
            "/api/career/subscriptions",
            headers=alpha,
            json={"name": "Python jobs", "query": "Python", "filters": {"scope": "live"}},
        )
        assert subscription.status_code == 200
        subscription_id = subscription.json()["id"]
        assert client.get("/api/career/subscriptions", headers=beta).json() == []

        delivery = client.post(f"/api/career/subscriptions/{subscription_id}/dispatch", headers=alpha, json={})
        assert delivery.status_code == 200
        assert delivery.json()["delivery"]["status"] == "preview_only"
        assert delivery.json()["configured"] is False
        assert client.post(f"/api/career/subscriptions/{subscription_id}/dispatch", headers=beta, json={}).status_code == 404


def test_workspace_profile_and_notifier_keep_delivery_truthful(tmp_path) -> None:
    workspace = CareerWorkspace(f"sqlite+pysqlite:///{tmp_path / 'workspace.db'}")
    workspace.create_schema()
    profile = workspace.update_profile(
        profile_key="one",
        display_name="One",
        email="one@example.test",
        target_roles=["data"],
    )
    assert profile["target_roles"] == ["data"]
    subscription = workspace.create_subscription("daily", "data", profile_key="one")
    assert workspace.active_subscription_targets()[0]["email"] == "one@example.test"

    from career_agent.platform.repository import JobRepository

    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}")
    repository.create_schema()
    notifier = SubscriptionNotifier(
        workspace,
        repository,
        SmtpSettings(host=None, port=587, username=None, password=None, sender=None, use_tls=True),
    )
    delivery = notifier.deliver(subscription, profile_key="one")
    assert delivery["delivery"]["status"] == "preview_only"
    assert delivery["configured"] is False
