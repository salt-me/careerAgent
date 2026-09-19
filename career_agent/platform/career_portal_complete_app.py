"""Composition root for the complete CareerAgent job-seeker experience."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .agentic_copilot import ToolCallingCareerAgent
from .career_copilot import CareerCopilot, CopilotRequest
from .career_portal_copilot import CAREER_PORTAL_COPILOT_HTML
from .career_portal_release_app import create_career_portal_release_app
from .freshness import freshness_report
from .identity import active_profile_key
from .notifications import SubscriptionNotifier
from .snapshot_reconciliation import verification_report
from .service import PlatformComponents
from .workspace import CareerWorkspace


class CareerProfileRequest(BaseModel):
    display_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=320)
    target_roles: list[str] = Field(default_factory=list, max_length=12)
    target_locations: list[str] = Field(default_factory=list, max_length=12)
    campus_cycle: str = Field(default="", max_length=64)
    employment_kind: str = Field(default="", max_length=32)


class CopilotPlanRequest(BaseModel):
    message: str = Field(default="", max_length=4_000)
    target_role: str = Field(default="", max_length=300)
    target_location: str = Field(default="", max_length=255)
    campus_cycle: str = Field(default="", max_length=64)
    employment_kind: str = Field(default="", max_length=32)
    resume_text: str = Field(default="", max_length=40_000)
    scope: str = Field(default="live", pattern="^(live|history|all)$")
    use_llm: bool = False


class SubscriptionDispatchRequest(BaseModel):
    recipient: str = Field(default="", max_length=320)


def create_complete_career_portal_app(components: PlatformComponents):
    app = create_career_portal_release_app(components)
    workspace = CareerWorkspace(components.repository.engine.url.render_as_string(hide_password=False))
    workspace.create_schema()
    notifier = SubscriptionNotifier(workspace, components.repository)
    copilot = CareerCopilot(components.repository, components.vector_store)
    agentic_copilot = ToolCallingCareerAgent(components.repository, components.vector_store)
    app.state.career_workspace = workspace
    app.state.subscription_notifier = notifier
    app.state.career_copilot = copilot
    if components.scheduler:
        components.scheduler.after_sync = notifier.dispatch_all

    app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != "/"]

    @app.get("/", response_class=HTMLResponse)
    def complete_portal() -> str:
        return CAREER_PORTAL_COPILOT_HTML

    @app.get("/api/career/freshness")
    def career_freshness() -> dict[str, Any]:
        return freshness_report(components.repository)

    @app.get("/api/career/verification")
    def career_verification() -> dict[str, Any]:
        return verification_report(components.repository)
    @app.get("/api/career/profile")
    def career_profile(profile_key: str = Depends(active_profile_key)) -> dict[str, Any]:
        return workspace.profile(profile_key)

    @app.put("/api/career/profile")
    def update_career_profile(payload: CareerProfileRequest, profile_key: str = Depends(active_profile_key)) -> dict[str, Any]:
        if payload.email and "@" not in payload.email:
            raise HTTPException(status_code=422, detail="email must contain @")
        return workspace.update_profile(
            profile_key=profile_key,
            display_name=payload.display_name,
            email=payload.email,
            target_roles=payload.target_roles,
            target_locations=payload.target_locations,
            campus_cycle=payload.campus_cycle,
            employment_kind=payload.employment_kind,
        )

    @app.post("/api/career/copilot/plan")
    def career_plan(payload: CopilotPlanRequest, profile_key: str = Depends(active_profile_key)) -> dict[str, Any]:
        profile = workspace.profile(profile_key)
        request = CopilotRequest(
            message=payload.message,
            target_role=payload.target_role or " ".join(profile["target_roles"]),
            target_location=payload.target_location or " ".join(profile["target_locations"]),
            campus_cycle=payload.campus_cycle or str(profile["campus_cycle"]),
            employment_kind=payload.employment_kind or str(profile["employment_kind"]),
            resume_text=payload.resume_text,
            scope=payload.scope,
        )
        return agentic_copilot.to_dict(request, use_llm=payload.use_llm)

    @app.post("/api/career/subscriptions/{subscription_id}/dispatch")
    def dispatch_subscription(
        subscription_id: int,
        payload: SubscriptionDispatchRequest,
        profile_key: str = Depends(active_profile_key),
    ) -> dict[str, Any]:
        subscription = workspace.subscription(subscription_id, profile_key)
        if subscription is None:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return notifier.deliver(subscription, profile_key=profile_key, recipient=payload.recipient or None)

    return app
