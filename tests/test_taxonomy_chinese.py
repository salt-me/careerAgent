from __future__ import annotations

from career_agent.platform.taxonomy import classify_job, cycle_guidance


def test_chinese_campus_internship_and_experienced_taxonomy() -> None:
    campus = classify_job("2027届秋招软件工程师")
    internship = classify_job("数据分析实习生")
    experienced = classify_job("3年经验财务主管（社招）")
    assert (campus.employment_kind, campus.campus_cycle, campus.job_group) == ("campus", "2027_autumn", "engineering")
    assert (internship.employment_kind, internship.job_group) == ("internship", "data")
    assert (experienced.employment_kind, experienced.job_group) == ("experienced", "finance")


def test_cycle_guidance_is_readable_chinese() -> None:
    assert "秋招" in cycle_guidance("2027_autumn", "campus")[0]
