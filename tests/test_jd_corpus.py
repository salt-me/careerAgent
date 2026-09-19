from __future__ import annotations

from career_agent.jd_corpus import find_curated_jd, load_curated_jds


def test_expanded_corpus_has_twelve_auditable_public_jds() -> None:
    jobs = load_curated_jds()
    assert len(jobs) == 12
    assert all(job["source"].startswith("https://") for job in jobs)
    assert all(job["captured_at"] == "2026-08-02" for job in jobs)


def test_expanded_corpus_can_find_agent_coding_role() -> None:
    job = find_curated_jd("xiaohongshu-19192-2026")
    assert "RAG" in job["text"]
