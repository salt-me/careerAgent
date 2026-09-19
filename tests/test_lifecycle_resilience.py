from career_agent.platform.connectors import IncomingJob, StaticConnector
from career_agent.platform.orchestration import SyncOrchestrator
from career_agent.platform.repository import JobRepository
from career_agent.platform.resilience import RetryPolicy, RetryingConnector


class FlakyConnector:
    name = "flaky"
    authoritative = True

    def __init__(self):
        self.calls = 0

    def fetch(self):
        self.calls += 1
        if self.calls < 3:
            raise OSError("temporary network failure")
        return [
            IncomingJob(
                source_name="flaky",
                external_id="1",
                source_url="https://jobs.example.test/1",
                company="Example",
                title="Engineer",
                description="Reliable service development.",
                declared_status="open",
            )
        ]


def test_retrying_connector_recovers_from_transient_failures():
    connector = FlakyConnector()
    wrapped = RetryingConnector(connector, RetryPolicy(max_attempts=3, base_delay_seconds=0))
    assert len(wrapped.fetch()) == 1
    assert connector.calls == 3


def test_first_failed_sync_records_a_source_health_failure(tmp_path) -> None:
    class FailingConnector:
        name = "always-fails"
        authoritative = False

        def fetch(self):
            raise OSError("source unavailable")

    repository = JobRepository(f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}")
    repository.create_schema()
    result = SyncOrchestrator(
        repository,
        [FailingConnector()],
        vector_store=None,
        missing_threshold=2,
        history_retention_days=1095,
    ).sync_one("always-fails")

    assert result.state == "failed"
    assert repository.source_health()[0]["consecutive_failures"] == 1
