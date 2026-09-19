"""One-time, guarded migration from a legacy SQLite platform database.

The command copies the lifecycle tables into an *empty* PostgreSQL database.
It intentionally refuses a non-empty target so an operator cannot overwrite a
running database by accident.  The SQLite source is opened read-only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select, text

from .models import Base, JobRecord, JobVersion, SourceHealth, SyncRun


TABLES = (JobRecord.__table__, JobVersion.__table__, SourceHealth.__table__, SyncRun.__table__)
DEFAULT_DATABASE_URL = "sqlite:///career_agent_platform.db"


def _read_only_sqlite_url(path: Path) -> str:
    return f"sqlite:///file:{path.resolve().as_posix()}?mode=ro&uri=true"


def _counts(connection: Any) -> dict[str, int]:
    return {table.name: int(connection.scalar(select(func.count()).select_from(table)) or 0) for table in TABLES}


def migrate(source_path: Path, database_url: str, *, dry_run: bool = False, batch_size: int = 500) -> dict[str, Any]:
    """Copy the lifecycle tables while preserving IDs, versions, and audit rows."""
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite source does not exist: {source_path}")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    source_engine = create_engine(_read_only_sqlite_url(source_path), future=True)
    target_engine = create_engine(database_url, future=True)
    try:
        with source_engine.connect() as source:
            source_counts = _counts(source)
            if source_counts["job_records"] == 0:
                raise ValueError("SQLite source contains no job_records")
            if dry_run:
                return {"dry_run": True, "source": str(source_path), "counts": source_counts}

            Base.metadata.create_all(target_engine)
            with target_engine.begin() as target:
                target_counts = _counts(target)
                if any(target_counts.values()):
                    raise ValueError(f"Refusing to overwrite a non-empty target database: {target_counts}")

                for table in TABLES:
                    batch: list[dict[str, Any]] = []
                    for row in source.execute(select(table)).mappings():
                        batch.append(dict(row))
                        if len(batch) >= batch_size:
                            target.execute(table.insert(), batch)
                            batch.clear()
                    if batch:
                        target.execute(table.insert(), batch)

                if target.dialect.name == "postgresql":
                    target.execute(
                        text(
                            "SELECT setval("
                            "pg_get_serial_sequence('job_versions', 'id'), "
                            "COALESCE((SELECT MAX(id) FROM job_versions), 1), true)"
                        )
                    )
                migrated_counts = _counts(target)
                if migrated_counts != source_counts:
                    raise RuntimeError(f"Post-migration count mismatch: source={source_counts}, target={migrated_counts}")
    finally:
        source_engine.dispose()
        target_engine.dispose()

    return {"dry_run": False, "source": str(source_path), "counts": source_counts}


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy a legacy CareerAgent SQLite history into an empty platform database.")
    parser.add_argument("--source", required=True, type=Path, help="Path to the legacy SQLite database")
    parser.add_argument("--database-url", default=os.getenv("CAREER_AGENT_DATABASE_URL", DEFAULT_DATABASE_URL))
    parser.add_argument("--dry-run", action="store_true", help="Validate and report source row counts without writing")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    print(json.dumps(migrate(args.source, args.database_url, dry_run=args.dry_run, batch_size=args.batch_size), ensure_ascii=False))


if __name__ == "__main__":
    main()
