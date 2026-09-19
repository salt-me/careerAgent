from career_agent.platform.lenovo_connector import LenovoCampusConnector


def _record(job_id: int, title: str) -> dict:
    return {
        "id": job_id,
        "jobName": title,
        "jobDuties": "<p>负责 <strong>平台</strong> 构建</p>",
        "jobRequirement": "<p>要求 Python</p>",
        "typeName": "研发类",
        "projectType": 1,
        "firstDeptId": 17,
        "educationRequired": "本科",
        "workPlace": "1,6",
        "hotFlag": 1,
    }


def test_lenovo_public_connector_pages_and_maps_the_complete_job_list() -> None:
    calls: list[dict] = []

    def fetch_json(_url: str, params: dict) -> dict:
        calls.append(params)
        if params["pageNum"] == 1:
            rows = [_record(101, "AI 工程师"), _record(102, "产品经理")]
        else:
            rows = [_record(103, "算法工程师")]
        return {"code": 0, "result": {"total": 3, "rows": rows}}

    connector = LenovoCampusConnector(fetch_json=fetch_json)
    jobs = connector.fetch()

    assert calls == [{"pageSize": 100, "pageNum": 1}, {"pageSize": 100, "pageNum": 2}]
    assert [job.external_id for job in jobs] == ["101", "102", "103"]
    assert jobs[0].source_name == "lenovo:china-public-jobbase-api"
    assert jobs[0].source_url == "https://talent.lenovo.com.cn/position/detail?id=101"
    assert jobs[0].description == "负责 平台 构建\n要求 Python"
    assert jobs[0].location == "not_disclosed"
    assert jobs[0].declared_status == "open"
    assert jobs[0].declared_group == "联想公开招聘 研发类"
    assert jobs[0].metadata["work_place_codes"] == "1,6"
    assert jobs[0].metadata["reported_total"] == "3"
    assert connector.authoritative is True
