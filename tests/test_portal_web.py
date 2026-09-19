from career_agent.platform.portal_web import PORTAL_WEB_HTML


def test_portal_web_escapes_selection_hint_newline_for_javascript() -> None:
    assert "selected.title+'\\n" in PORTAL_WEB_HTML
    assert "selected.title+'\n" not in PORTAL_WEB_HTML
