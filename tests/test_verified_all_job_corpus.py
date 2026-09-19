import json

from career_agent.verified_all_job_corpus import large_coverage_report, load_verified_all_job_records


def test_keeps_multiple_postings_from_one_company_and_enforces_function_coverage(tmp_path):
    path = tmp_path / "cc0.jsonl"
    rows = []
    for number in range(11):
        company = "Repeated Co" if number < 2 else f"Company {number}"
        rows.append(
            {
                "source_url": f"https://jobs.example.test/{number}",
                "source_job_id": f"job-{number}",
                "source_status": "unknown",
                "title": "Software Engineer",
                "company": company,
                "position": "engineering",
                "job_family": "engineering",
                "location": "Remote",
                "captured_at": "2026-08-02",
                "text": "Build a reliable software service with collaborators and document production operations.",
            }
        )
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    records, deduplication = load_verified_all_job_records(licensed_paths=[path], include_seed=False)
    report = large_coverage_report(records, target_record_count=11, min_companies_per_position=10)

    assert len(records) == 11
    assert deduplication["exact_source_duplicates_removed"] == 0
    assert report["positions"]["engineering"]["different_company_count"] == 10
    assert report["all_position_groups_meet_company_minimum"] is True
