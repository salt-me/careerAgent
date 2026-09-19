from career_agent.platform.china_connectors import PddCampusPageConnector


def test_pdd_public_campus_connector_pages_and_maps_open_jobs() -> None:
    calls: list[dict] = []

    def fetch_json(_url: str, payload: dict) -> dict:
        calls.append(payload)
        if payload["page"] == 1:
            return {
                "success": True,
                "result": {
                    "total": "3",
                    "list": [
                        {
                            "id": "position-1",
                            "code": "XZ-1",
                            "name": "AI Agent研发工程师",
                            "workLocationName": "上海",
                            "job": "technology",
                            "jobName": "技术",
                            "releaseTime": 1783256970000,
                            "jobDuty": "负责 Agent 核心架构开发。",
                            "labelList": ["紧缺"],
                            "recruitTypeName": "技术专场",
                            "graduationYear": "2027",
                        },
                        {
                            "id": "position-2",
                            "code": "XZ-2",
                            "name": "算法工程师",
                            "workLocation": "上海",
                            "job": "technology",
                            "jobName": "技术",
                            "releaseTime": 1783256958000,
                            "jobDuty": "负责机器学习平台优化。",
                            "labelList": [],
                            "recruitTypeName": "技术专场",
                            "graduationYear": "2027",
                        },
                    ],
                },
            }
        return {
            "success": True,
            "result": {
                "total": "3",
                "list": [
                    {
                        "id": "position-3",
                        "code": "XZ-3",
                        "name": "产品经理",
                        "workLocation": "上海",
                        "job": "product",
                        "jobName": "产品",
                        "releaseTime": 1783256937000,
                        "jobDuty": "负责产品规划。",
                        "labelList": [],
                        "recruitTypeName": "管培生",
                        "graduationYear": "2027",
                    }
                ],
            },
        }

    connector = PddCampusPageConnector(fetch_json=fetch_json)
    jobs = connector.fetch()

    assert calls == [{"page": 1, "pageSize": 20}, {"page": 2, "pageSize": 20}]
    assert [job.external_id for job in jobs] == ["position-1", "position-2", "position-3"]
    assert jobs[0].source_name == "pdd:campus-public-api"
    assert jobs[0].source_url.endswith("positionId=position-1")
    assert jobs[0].declared_status == "open"
    assert "2027届 校招 技术专场 技术" == jobs[0].declared_group
    assert jobs[0].metadata["labels"] == ["紧缺"]
    assert connector.authoritative is False
