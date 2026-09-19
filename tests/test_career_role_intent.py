from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.platform.career_portal_complete_app import create_complete_career_portal_app
from career_agent.platform.connectors import IncomingJob


def test_product_query_uses_role_intent_not_incidental_product_word(platform_components) -> None:
    platform_components.repository.apply_sync(
        "role-intent-source",
        [
            IncomingJob("role-intent-source", "pm", "https://example.test/pm", "Acme", "Product Manager", "Own roadmap.", declared_status="open"),
            IncomingJob("role-intent-source", "pe", "https://example.test/pe", "Acme", "Product Security Engineer", "Secure product systems.", declared_status="open"),
            IncomingJob("role-intent-source", "pd", "https://example.test/pd", "Acme", "Product Designer", "Design product UI.", declared_status="open"),
            IncomingJob("role-intent-source", "pmkt", "https://example.test/pmkt", "Acme", "Product Marketing Manager", "Market products.", declared_status="open"),
        ],
        authoritative=False,
        missing_threshold=2,
    )
    app = create_complete_career_portal_app(platform_components)
    with TestClient(app) as client:
        result = client.get("/api/career/search", params={"query": "Product", "scope": "live"}).json()

    assert result["match_mode"] == "title_or_category_exact"
    assert {item["title"] for item in result["items"]} == {"Product Manager"}
