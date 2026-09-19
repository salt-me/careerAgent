from career_agent.platform.portal_web_v2 import PORTAL_WEB_V2_HTML


def test_portal_cleans_raw_html_excerpt_before_safe_rendering() -> None:
    assert "function cleanExcerpt(value)" in PORTAL_WEB_V2_HTML
    assert "esc(cleanExcerpt(j.excerpt)).slice(0,250)" in PORTAL_WEB_V2_HTML
    assert "${esc(j.excerpt).slice(0,250)}" not in PORTAL_WEB_V2_HTML
