"""Runtime configuration for the CareerAgent lifecycle platform."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class PlatformSettings:
    database_url: str
    qdrant_url: str | None
    qdrant_path: Path
    embedding_model: str
    missing_sync_threshold: int
    history_retention_days: int
    admin_token: str | None
    scheduler_enabled: bool
    scheduler_hour_utc: int
    greenhouse_boards: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "PlatformSettings":
        boards = tuple(
            item.strip() for item in os.getenv("CAREER_AGENT_GREENHOUSE_BOARDS", "").split(",") if item.strip()
        )
        return cls(
            # Local development defaults to SQLite. Production compose always
            # supplies a postgresql+psycopg URL.
            database_url=os.getenv("CAREER_AGENT_DATABASE_URL", "sqlite+pysqlite:///career_agent_platform.db"),
            qdrant_url=os.getenv("CAREER_AGENT_QDRANT_URL") or None,
            qdrant_path=Path(os.getenv("CAREER_AGENT_QDRANT_PATH", "qdrant_storage/career_agent_lifecycle")),
            embedding_model=os.getenv(
                "CAREER_AGENT_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"
            ),
            missing_sync_threshold=int(os.getenv("CAREER_AGENT_MISSING_SYNC_THRESHOLD", "2")),
            history_retention_days=int(os.getenv("CAREER_AGENT_HISTORY_RETENTION_DAYS", "1095")),
            admin_token=os.getenv("CAREER_AGENT_ADMIN_TOKEN") or None,
            scheduler_enabled=_bool(os.getenv("CAREER_AGENT_SCHEDULER_ENABLED")),
            scheduler_hour_utc=int(os.getenv("CAREER_AGENT_SCHEDULER_HOUR_UTC", "2")),
            greenhouse_boards=boards,
        )

    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql+") or self.database_url.startswith("postgres://")

