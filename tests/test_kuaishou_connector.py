from career_agent.platform.kuaishou_connector import KuaishouCampus2027Connector


def test_kuaishou_connector_maps_public_job_payload() -> None:
    connector = KuaishouCampus2027Connector(
        fetch_json=lambda _url, _payload: {
            "code": 0,
            "result": {
                "total": 1,
                "list": [
                    {
                        "id": 42,
                        "name": "大模型应用算法工程师",
                        "description": "负责大模型应用落地。",
                        "positionDemand": "熟悉 Python。",
                        "workLocationDicts": [{"name": "北京"}, {"name": "杭州"}],
                        "releaseTime": "2026-08-01 10:00:00",
                        "recruitProjectCode": "schoolr",
                        "recruitSubProjectCode": "20271779425607",
                        "positionCategoryCode": "J1003",
                        "positionStatusCode": "Release",
                    }
                ],
            },
        }
    )

    jobs = connector.fetch()

    assert len(jobs) == 1
    assert jobs[0].source_name == "kuaishou:campus-2027-public-api"
    assert jobs[0].company == "快手"
    assert jobs[0].location == "北京、杭州"
    assert jobs[0].declared_status == "open"
    assert jobs[0].declared_group == "2027届校招"
    assert jobs[0].metadata["position_status_code"] == "Release"
