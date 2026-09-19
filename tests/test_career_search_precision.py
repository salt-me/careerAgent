from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.platform.career_portal_complete_app import create_complete_career_portal_app
from career_agent.platform.connectors import IncomingJob


def _job(external_id: str, *, company: str, title: str, description: str = "") -> IncomingJob:
    return IncomingJob(
        source_name="precision-test-source",
        external_id=external_id,
        source_url=f"https://jobs.example.test/{external_id}",
        company=company,
        title=title,
        description=description or title,
        location="Beijing",
        declared_status="open",
    )


def test_search_returns_all_exact_matches_and_never_leaks_other_companies(platform_components) -> None:
    jobs = [
        *[_job(f"eng-{index}", company="Precision", title=f"Engineer {index}") for index in range(25)],
        _job("baidu-product", company="Baidu", title="Product Manager"),
        _job("baidu-engineer", company="Baidu", title="Platform Engineer"),
        _job("other-mentions-baidu", company="Other", title="Backend Engineer", description="Integrates with Baidu APIs."),
        _job("product-title", company="Acme", title="Product Analyst"),
        _job("product-description-only", company="Other", title="Operations Specialist", description="Supports product launches."),
    ]
    platform_components.repository.apply_sync(
        "precision-test-source", jobs, authoritative=False, missing_threshold=2
    )
    app = create_complete_career_portal_app(platform_components)

    with TestClient(app) as client:
        all_engineers = client.get("/api/career/search", params={"query": "Engineer", "scope": "live"})
        assert all_engineers.status_code == 200
        engineer_payload = all_engineers.json()
        assert engineer_payload["all_results"] is True
        assert engineer_payload["total_matches"] == len(engineer_payload["items"])
        assert engineer_payload["total_matches"] > 20

        baidu = client.get("/api/career/search", params={"query": "Baidu", "scope": "live"}).json()
        assert baidu["match_mode"] == "company_exact"
        assert {item["company"] for item in baidu["items"]} == {"Baidu"}
        assert baidu["total_matches"] == 2

        product = client.get("/api/career/search", params={"query": "Product", "scope": "live"}).json()
        assert product["match_mode"] == "title_or_category_exact"
        assert {item["title"] for item in product["items"]} >= {"Product Manager", "Product Analyst"}
        assert "Operations Specialist" not in {item["title"] for item in product["items"]}
