"""Refresh normalized taxonomy and optionally re-index changed job records."""

from __future__ import annotations

import argparse

from .platform.config import PlatformSettings
from .platform.repository import JobRepository
from .platform.taxonomy_backfill import refresh_job_taxonomy
from .platform.vector_store import LifecycleVectorStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="incrementally update Qdrant points for changed records")
    args = parser.parse_args()
    settings = PlatformSettings.from_env()
    repository = JobRepository(settings.database_url)
    repository.create_schema()
    result = refresh_job_taxonomy(repository)
    output = {"scanned": result.scanned, "changed": result.changed}
    if args.reindex and result.affected_ids:
        vector = LifecycleVectorStore(repository, model_name=settings.embedding_model, qdrant_url=settings.qdrant_url, qdrant_path=settings.qdrant_path)
        output["reindexed"] = vector.sync_jobs(repository.get_many(result.affected_ids))
    print(output)


if __name__ == "__main__":
    main()
