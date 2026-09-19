from career_agent.enterprise_corpus import enterprise_report, load_enterprise_job_records


def test_enterprise_production_batch_has_one_hundred_new_companies_and_keeps_coverage():
    records, _ = load_enterprise_job_records()
    report = enterprise_report(records)

    assert report["record_count"] >= 10_000
    assert report["all_position_groups_meet_company_minimum"] is True
    assert report["official_enterprise_summary"]["net_new_companies"] >= 100
    assert report["official_enterprise_summary"]["records"] >= 1_000
