"""Bounded retry wrapper for transient connector failures."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .connectors import IncomingJob, JobConnector


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0


class RetryingConnector:
    """Retry a connector fetch without duplicating a repository sync run."""

    def __init__(self, connector: JobConnector, policy: RetryPolicy = RetryPolicy()) -> None:
        self.connector = connector
        self.name = connector.name
        self.authoritative = connector.authoritative
        self.policy = policy

    def fetch(self) -> list[IncomingJob]:
        last_error: Exception | None = None
        for attempt in range(self.policy.max_attempts):
            try:
                return self.connector.fetch()
            except Exception as error:
                last_error = error
                if attempt + 1 < self.policy.max_attempts:
                    time.sleep(self.policy.base_delay_seconds * (2**attempt))
        assert last_error is not None
        raise RuntimeError(f"Connector {self.name} failed after {self.policy.max_attempts} attempts") from last_error

