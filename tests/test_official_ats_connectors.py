from career_agent.platform.official_ats_connectors import AshbyConnector, LeverConnector


def test_lever_connector_normalises_published_job() -> None:
    connector = LeverConnector(
        "sample",
        fetch_json=lambda _: [
            {
                "id": "lever-1",
                "text": "Data Engineer",
                "hostedUrl": "https://jobs.lever.co/sample/lever-1",
                "descriptionPlain": "Build reliable pipelines using Python and SQL.",
                "createdAt": 1_700_000_000_000,
                "categories": {"location": "Remote", "department": "Data", "team": "Platform"},
            }
        ],
    )

    [job] = connector.fetch()
    assert job.source_name == "lever:sample"
    assert job.declared_status == "open"
    assert job.location == "Remote"
    assert job.published_at and job.published_at.endswith("+00:00")


def test_ashby_connector_excludes_unlisted_job() -> None:
    connector = AshbyConnector(
        "sample",
        fetch_json=lambda _: {
            "jobs": [
                {
                    "id": "ashby-1",
                    "title": "Machine Learning Intern",
                    "jobUrl": "https://jobs.ashbyhq.com/sample/ashby-1",
                    "descriptionPlain": "Build ML evaluation tools.",
                    "location": "Shanghai",
                    "department": "Engineering",
                    "isListed": True,
                },
                {"id": "private", "title": "Private", "jobUrl": "https://example.com", "isListed": False},
            ]
        },
    )

    jobs = connector.fetch()
    assert len(jobs) == 1
    assert jobs[0].source_name == "ashby:sample"
    assert jobs[0].metadata["connector"] == "ashby"
