from career_agent.universal_corpus import corpus_summary, find_universal_record, load_universal_records
from career_agent.universal_matching import build_universal_match


def test_universal_corpus_keeps_actionable_jobs_separate_from_profiles() -> None:
    summary = corpus_summary()
    records = load_universal_records()
    assert summary["record_count"] >= 35
    assert summary["actionable_public_jd_count"] >= 19
    assert summary["job_family_count"] >= 15
    assert any(record["artifact_type"] == "job_family_profile" and not record["live_vacancy"] for record in records)
    assert any(record["artifact_type"] == "public_jd" and record["live_vacancy"] for record in records)


def test_universal_match_supports_non_ai_roles_and_discloses_profile_boundary() -> None:
    record = find_universal_record("profile-data-analyst-20260802")
    result = build_universal_match("我用 SQL、Python、Excel 做过指标体系、数据清洗和 Power BI 看板。", record)
    assert "SQL" in result.matched_skills
    assert result.boundary_notice is not None
    assert result.match_score >= 50


def test_universal_match_handles_official_job_without_profile_warning() -> None:
    record = find_universal_record("baidu-j100737-backend-20260802")
    result = build_universal_match("熟悉 Java、SQL、Linux、数据结构、算法和分布式系统。", record)
    assert result.boundary_notice is None
    assert "Java" in result.matched_skills
