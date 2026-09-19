"""Release app joins personal resume parsing and subscription-hit preview APIs."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from .career_portal_production_app import create_career_portal_production_app
from .career_portal_release import CAREER_PORTAL_RELEASE_HTML
from .official_source_contracts import configured_official_json_contracts
from .identity import active_profile_key
from .resume_parser import ResumeParseError, parse_resume_bytes
from .service import PlatformComponents
from .subscription_matching import subscription_preview


def create_career_portal_release_app(components: PlatformComponents):
    app = create_career_portal_production_app(components)
    app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != "/"]

    @app.get("/", response_class=HTMLResponse)
    def release_portal() -> str:
        return CAREER_PORTAL_RELEASE_HTML

    @app.post("/api/career/resume/parse")
    async def parse_resume(request: Request, filename: str = "resume.txt") -> dict:
        try:
            profile = parse_resume_bytes(await request.body(), filename, request.headers.get("content-type", ""))
        except ResumeParseError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return profile.to_dict()

    @app.get("/api/career/subscriptions/{subscription_id}/preview")
    def preview_subscription(subscription_id: int, fresh_hours: int = 24, profile_key: str = Depends(active_profile_key)) -> dict:
        subscription = next((item for item in components.repository.engine and _workspace_subscriptions(app, profile_key) if item["id"] == subscription_id), None)
        if subscription is None:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return subscription_preview(components.repository, subscription, fresh_hours=max(1, min(fresh_hours, 24 * 30)))

    @app.get("/api/career/source-contracts")
    def active_source_contracts() -> list[dict]:
        return [
            {"source_name": connector.name, "authoritative": connector.authoritative, "company": connector.contract["company"], "feed_url": connector.contract["feed_url"]}
            for connector in configured_official_json_contracts()
        ]

    return app


def _workspace_subscriptions(app, profile_key: str = "local") -> list[dict]:
    """Reach existing app's public API storage without duplicating its schema."""
    workspace = getattr(app.state, "career_workspace", None)
    if workspace is None:
        # The base factory stores no public reference.  It is attached by the
        # release factory's caller immediately after creation below.
        return []
    return workspace.subscriptions(profile_key=profile_key)
