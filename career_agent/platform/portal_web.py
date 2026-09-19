"""Corrected candidate-facing portal with valid JavaScript string escaping."""

from __future__ import annotations

from fastapi.responses import HTMLResponse

from .portal import PORTAL_HTML
from .service import PlatformComponents, create_platform_app


# ``PORTAL_HTML`` was authored as a Python multiline literal.  Its JavaScript
# selection hint needs a literal ``\\n`` escape rather than a physical newline
# inside a JavaScript single-quoted string.
PORTAL_WEB_HTML = PORTAL_HTML.replace("selected.title+'\n", "selected.title+'\\n")


def create_career_portal_web_app(components: PlatformComponents):
    app = create_platform_app(components)

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    def candidate_portal() -> str:
        return PORTAL_WEB_HTML

    return app
