from __future__ import annotations

from career_agent.public_jds import find_public_jd, load_public_jds


def test_public_jd_seed_data_has_auditable_provenance() -> None:
    jobs = load_public_jds()
    assert len(jobs) == 3
    assert all(job["source"].startswith("https://") for job in jobs)
    assert all(job["captured_at"] == "2026-08-01" for job in jobs)


def test_public_jd_lookup_is_stable() -> None:
    job = find_public_jd("xiaohongshu-18716-2026")
    assert job["company"] == "小红书"
    assert "Agent" in job["text"]
