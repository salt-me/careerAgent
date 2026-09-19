from __future__ import annotations

from career_agent.platform.career_intelligence import build_match_insight, clean_text, hybrid_rerank


def test_clean_text_removes_html_and_entities() -> None:
    assert clean_text("<p><strong>Software&nbsp;Engineer</strong></p>") == "Software Engineer"


def test_hybrid_rerank_prefers_exact_title_and_merges_cross_source_duplicate() -> None:
    jobs = [
        {"id": "a", "company": "Example", "title": "Python Software Engineer", "location": "Beijing", "text": "Python backend service", "last_verified_at": "2026-08-03T00:00:00+00:00"},
        {"id": "b", "company": "Example", "title": "Python Software Engineer", "location": "Beijing", "text": "Python backend service", "last_verified_at": "2026-08-03T00:00:00+00:00"},
        {"id": "c", "company": "Other", "title": "Operations Associate", "location": "Shanghai", "text": "Operations role", "last_verified_at": "2026-08-03T00:00:00+00:00"},
    ]
    results = hybrid_rerank("python engineer", jobs, {"a": 0.8, "b": 0.7, "c": 0.95})
    assert len(results) == 2
    assert results[0]["id"] == "a"
    assert results[0]["duplicate_count"] == 2


def test_match_insight_explains_skill_gaps_without_hiring_prediction() -> None:
    result = build_match_insight("Python SQL project", {"title": "Data Engineer", "text": "Python SQL Docker Kubernetes", "lifecycle_status": "open"})
    assert "Python" in result.matched_skills
    assert "Docker" in result.missing_skills
    assert "not a hiring" in result.boundary_notice.lower()
