from fastapi.testclient import TestClient

from career_agent.platform.portal import create_career_portal_app
from career_agent.platform.service import PlatformComponents


def test_candidate_portal_is_served(platform_components: PlatformComponents) -> None:
    app = create_career_portal_app(platform_components)
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "CareerAgent" in response.text
    assert "岗位发现与准备助手" in response.text
