import pytest

from career_agent.scalable_corpus import CorpusValidationError, coverage_report, load_scalable_job_records, validate_and_normalise


def test_scalable_corpus_records_have_auditable_sources_and_backend_has_ten_companies() -> None:
    records, deduplication = load_scalable_job_records()
    report = coverage_report(records)
    backend = report["positions"]["后端研发工程师"]
    assert report["source_distribution"]["liepin"] >= 3
    assert report["source_distribution"]["nowcoder"] >= 10
    assert backend["different_company_count"] >= 10
    assert backend["meets_minimum"] is True
    assert deduplication["url_duplicates_removed"] == 0
    assert all(record["source_url"].startswith("https://") for record in records)


def test_scalable_validation_rejects_untraceable_or_short_records() -> None:
    with pytest.raises(CorpusValidationError, match="source_url"):
        validate_and_normalise(
            {
                "source_name": "nowcoder",
                "source_url": "not-a-url",
                "title": "后端工程师",
                "company": "示例公司",
                "location": "北京",
                "text": "这是足够长但没有有效来源地址的公开职位摘要，用于校验。",
                "captured_at": "2026-08-02",
            }
        )


def test_scalable_validation_generates_stable_id() -> None:
    raw = {
        "source_name": "liepin",
        "source_url": "https://www.liepin.com/job/example.shtml?tracking=1",
        "title": "后端开发工程师",
        "company": "示例科技有限公司",
        "location": "北京",
        "text": "这是足够长的人工审阅公开职位摘要，用于测试可审计的标准化记录与稳定标识生成。",
        "captured_at": "2026-08-02",
    }
    assert validate_and_normalise(raw)["id"] == validate_and_normalise(raw)["id"]
