from career_agent.production_corpus import load_production_job_records, production_report


def test_production_corpus_has_10k_records_and_ten_companies_per_job_group():
    records, _ = load_production_job_records()
    report = production_report(records)

    assert report["record_count"] >= 10_000
    assert report["all_position_groups_meet_company_minimum"] is True
    assert report["chinese_platform_summary"]["nowcoder_record_count"] >= 300
    assert report["chinese_platform_summary"]["nowcoder_different_company_count"] >= 10
