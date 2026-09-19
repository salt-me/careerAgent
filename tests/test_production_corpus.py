import json

from career_agent.production_corpus import _normalise_platform_record, _platform_group


def test_platform_direction_mapping_uses_existing_function_groups():
    assert _platform_group("前端开发工程师", "前端开发") == "engineering"
    assert _platform_group("算法工程师", "大数据/算法/数据挖掘/机器学习/数据分析") == "data"
    assert _platform_group("产品经理", "产品类") == "product"


def test_platform_record_keeps_unique_job_identity_and_closed_status():
    raw = {
        "source_name": "nowcoder",
        "source_url": "https://www.nowcoder.com/careers/nowcoder1/413?jobIds=99",
        "source_job_id": "nowcoder-careers-413-99",
        "source_status": "closed",
        "title": "前端工程师",
        "company": "示例科技",
        "position": "前端开发",
        "location": "北京",
        "captured_at": "2026-08-02",
        "text": "牛客公开职位摘要：示例科技的前端工程师，页面显示职位已结束并保留原始职位标识供审计复核。",
    }
    result = _normalise_platform_record(raw)
    assert result["id"].startswith("nowcoder-")
    assert result["position"] == "engineering"
    assert result["source_status"] == "closed"
