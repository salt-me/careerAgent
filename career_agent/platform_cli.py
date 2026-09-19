"""CLI for schema setup, reviewed imports, syncing, and dual-index rebuilds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .platform.bootstrap import configured_connectors, snapshot_connector
from .platform.config import PlatformSettings
from .platform.orchestration import SyncOrchestrator
from .platform.quality import quality_report
from .platform.repository import JobRepository
from .platform.vector_store import LifecycleVectorStore


def _runtime(settings: PlatformSettings, connectors):
    repository = JobRepository(settings.database_url)
    repository.create_schema()
    vector = LifecycleVectorStore(
        repository,
        model_name=settings.embedding_model,
        qdrant_url=settings.qdrant_url,
        qdrant_path=settings.qdrant_path,
    )
    return repository, vector, SyncOrchestrator(
        repository,
        connectors,
        vector_store=vector,
        missing_threshold=settings.missing_sync_threshold,
        history_retention_days=settings.history_retention_days,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="CareerAgent lifecycle platform")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")
    commands.add_parser("sync")
    commands.add_parser("rebuild-index")
    commands.add_parser("quality")
    import_parser = commands.add_parser("import-snapshot")
    import_parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    settings = PlatformSettings.from_env()

    if args.command == "init-db":
        repository = JobRepository(settings.database_url)
        repository.create_schema()
        print(json.dumps({"database_url": settings.database_url, "schema": "created"}, ensure_ascii=False))
        return
    connectors = configured_connectors(settings)
    if args.command == "import-snapshot":
        connectors.append(snapshot_connector(args.paths))
    repository, vector, orchestrator = _runtime(settings, connectors)
    if args.command == "sync" or args.command == "import-snapshot":
        print(json.dumps([item.to_dict() for item in orchestrator.sync_all()], ensure_ascii=False, indent=2))
    elif args.command == "rebuild-index":
        print(json.dumps(vector.rebuild(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(quality_report(repository), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

