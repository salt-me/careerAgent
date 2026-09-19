"""Run a resumable verification pass against supported official ATS sources."""

from __future__ import annotations

import json

from .config import PlatformSettings
from .repository import JobRepository
from .vector_store import LifecycleVectorStore
from .verification_service import run_snapshot_verification


def main() -> None:
    settings = PlatformSettings.from_env()
    repository = JobRepository(settings.database_url)
    store = LifecycleVectorStore(
        repository,
        model_name=settings.embedding_model,
        qdrant_url=settings.qdrant_url,
        qdrant_path=settings.qdrant_path,
    )
    print(json.dumps(run_snapshot_verification(repository, store), ensure_ascii=False))


if __name__ == "__main__":
    main()
