"""Final portal factory: replaces compatibility root routes with production UI."""

from __future__ import annotations

from fastapi.responses import HTMLResponse

from .career_portal_next_app import create_career_portal_next_app
from .career_portal_production import CAREER_PORTAL_PRODUCTION_HTML
from .governance_extended import production_governance_report
from .official_china_catalog import china_source_catalog
from .service import PlatformComponents


def create_career_portal_production_app(components: PlatformComponents):
    app = create_career_portal_next_app(components)
    replace_paths = {"/", "/api/career/data-quality"}
    app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) not in replace_paths]

    @app.get("/", response_class=HTMLResponse)
    def production_portal() -> str:
        return CAREER_PORTAL_PRODUCTION_HTML

    @app.get("/api/career/data-quality")
    def production_quality() -> dict:
        return production_governance_report(components.repository)

    @app.get("/api/career/source-catalog")
    def source_catalog() -> list[dict[str, str]]:
        return china_source_catalog()

    return app
