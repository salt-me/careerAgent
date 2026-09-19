"""Candidate portal that renders raw-JD excerpts as readable plain text."""

from __future__ import annotations

from fastapi.responses import HTMLResponse

from .portal_web import PORTAL_WEB_HTML
from .service import PlatformComponents, create_platform_app


_CLEAN_EXCERPT = r"""function cleanExcerpt(value){let text=String(value||'');const decoder=document.createElement('textarea');decoder.innerHTML=text;text=decoder.value;return text.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim()}"""

# Clean source markup first, then use the existing esc() call when interpolation
# builds the card.  This retains XSS-safe rendering while hiding presentation
# tags, Office metadata attributes and encoded non-breaking spaces.
PORTAL_WEB_V2_HTML = (
    PORTAL_WEB_HTML.replace("function draw(items){", f"{_CLEAN_EXCERPT}function draw(items){{")
    .replace("${esc(j.excerpt).slice(0,250)}", "${esc(cleanExcerpt(j.excerpt)).slice(0,250)}")
)


def create_career_portal_web_v2_app(components: PlatformComponents):
    app = create_platform_app(components)

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    def candidate_portal() -> str:
        return PORTAL_WEB_V2_HTML

    return app
