"""One-way, safety-checked import of a legacy CareerAgent SQLite database."""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterator
from datetime import datetime, timezone
from itertools import islice
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, func, insert, select, text

from .models import Base, JobRecord, JobVersion, SourceHealth, SyncRun


TABLES = (JobRecord.__table__, JobVersion.__table__, SourceHealth.__table__, SyncRun.__table__)


def _batches(rows: Iterator[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    while batch := list(islice(rows, size)):
        yield batch


def _normalise(value: Any) -> Any:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _copy_table(source: Engine, target: Connection, table_name: str, *, batch_size: int) -> int:
    table = Base.metadata.tables[table_name]
    with source.connect() as connection:
        result = connection.execute(select(table))
        rows = (dict(row._mapping) for row in result)
        copied = 0
        for batch in _batches(rows, batch_size):
            prepared = [{key: _normalise(value) for key, value in row.items()} for row in batch]
            if table_name == JobVersion.__tablename__:
                for row in prepared:
                    row.pop("id", None)
            target.execute(insert(table), prepared)
            copied += len(prepared)
    return copied


def migrate(source_url: str, target_url: str, *, batch_size: int = 500) -> dict[str, int]:
    source = create_engine(source_url, future=True)
    target = create_engine(target_url, future=True)
    if not source.url.drivername.startswith("sqlite"):
        raise ValueError("source must be a SQLite URL")
    if target.url.drivername.startswith("sqlite"):
        raise ValueError("target must be a non-SQLite production database")

    Base.metadata.create_all(target)
    with target.begin() as connection:
        connection.execute(text("ALTER TABLE job_records ALTER COLUMN location TYPE TEXT"))
        existing = connection.scalar(select(func.count()).select_from(JobRecord)) or 0
    if existing:
        raise RuntimeError(f"target job_records is not empty ({existing}); refusing to merge")

    with target.begin() as connection:
        copied = {table.name: _copy_table(source, connection, table.name, batch_size=batch_size) for table in TABLES}
    return {"jobs": copied[JobRecord.__tablename__], "versions": copied[JobVersion.__tablename__], "sources": copied[SourceHealth.__tablename__], "sync_runs": copied[SyncRun.__tablename__]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the legacy SQLite corpus into an empty production database.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--target-url", default=os.getenv("CAREER_AGENT_DATABASE_URL", ""))
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    if not args.target_url:
        parser.error("--target-url or CAREER_AGENT_DATABASE_URL is required")
    print(migrate(args.source_url, args.target_url, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
