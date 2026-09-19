"""PostgreSQL-compatible persistence and lifecycle transitions."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import Engine, create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from .connectors import IncomingJob
from .models import Base, JobRecord, JobVersion, SourceHealth, SyncRun
from .taxonomy import classify_job


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _company_key(company: str) -> str:
    return "".join(character for character in company.casefold() if character.isalnum() or "\u4e00" <= character <= "\u9fff")


def _hash(job: IncomingJob) -> str:
    fields = (job.title, job.company, job.location, job.description, job.source_url, job.declared_status)
    return hashlib.sha256("\x1f".join(fields).encode("utf-8")).hexdigest()


def _initial_status(declared_status: str) -> str:
    status = declared_status.casefold()
    if status == "open":
        return "open"
    if status in {"closed", "expired", "historical"}:
        return "historical"
    return "unverified"


def job_to_dict(job: JobRecord) -> dict[str, Any]:
    return {
        "id": job.id,
        "source_name": job.source_name,
        "external_id": job.external_id,
        "source_url": job.source_url,
        "company": job.company,
        "company_key": job.company_key,
        "title": job.title,
        "location": job.location,
        "language": job.language,
        "job_group": job.job_group,
        "employment_kind": job.employment_kind,
        "campus_cycle": job.campus_cycle,
        "lifecycle_status": job.lifecycle_status,
        "status_reason": job.status_reason,
        "text": job.description,
        "metadata": job.metadata_json,
        "first_seen_at": job.first_seen_at.isoformat(),
        "last_seen_at": job.last_seen_at.isoformat(),
        "last_verified_at": job.last_verified_at.isoformat() if job.last_verified_at else None,
        "archived_at": job.archived_at.isoformat() if job.archived_at else None,
    }


@dataclass(frozen=True)
class SyncStats:
    source_name: str
    fetched: int
    created: int
    updated: int
    unchanged: int
    archived: int
    affected_ids: tuple[str, ...]


class JobRepository:
    def __init__(self, database_url: str, *, engine: Engine | None = None) -> None:
        self.engine = engine or create_engine(database_url, future=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, future=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def begin_run(self, source_name: str, started_at: datetime | None = None) -> str:
        run_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            session.add(SyncRun(id=run_id, source_name=source_name, started_at=started_at or utcnow(), state="running"))
        return run_id

    def finish_run(self, run_id: str, stats: SyncStats | None = None, error: str | None = None) -> None:
        with self.sessions.begin() as session:
            run = session.get(SyncRun, run_id)
            if run is None:
                return
            run.finished_at = utcnow()
            if error:
                run.state = "failed"
                run.error = error[:4000]
            else:
                assert stats is not None
                run.state = "succeeded"
                run.fetched_count = stats.fetched
                run.created_count = stats.created
                run.updated_count = stats.updated
                run.archived_count = stats.archived

    def record_health(self, source_name: str, *, success: bool, record_count: int | None, error: str | None = None) -> None:
        now = utcnow()
        with self.sessions.begin() as session:
            health = session.get(SourceHealth, source_name)
            if health is None:
                health = SourceHealth(source_name=source_name, last_attempt_at=now, consecutive_failures=0)
                session.add(health)
            health.last_attempt_at = now
            if success:
                health.last_success_at = now
                health.last_record_count = record_count
                health.consecutive_failures = 0
                health.last_error = None
            else:
                health.consecutive_failures += 1
                health.last_error = (error or "unknown connector error")[:4000]

    def apply_sync(
        self,
        source_name: str,
        jobs: Iterable[IncomingJob],
        *,
        authoritative: bool,
        missing_threshold: int,
        observed_at: datetime | None = None,
    ) -> SyncStats:
        observed_at = observed_at or utcnow()
        created = updated = unchanged = archived = 0
        affected: set[str] = set()
        materialized = list(jobs)
        source_names = {job.source_name for job in materialized} or {source_name}
        with self.sessions.begin() as session:
            for incoming in materialized:
                taxonomy = classify_job(incoming.title, incoming.description, incoming.declared_group)
                digest = _hash(incoming)
                job = session.scalar(
                    select(JobRecord).where(
                        JobRecord.source_name == incoming.source_name, JobRecord.external_id == incoming.external_id
                    )
                )
                next_status = _initial_status(incoming.declared_status)
                if job is None:
                    job = JobRecord(
                        id=str(uuid.uuid4()),
                        source_name=incoming.source_name,
                        external_id=incoming.external_id,
                        source_url=incoming.source_url,
                        company=incoming.company,
                        company_key=_company_key(incoming.company),
                        title=incoming.title,
                        location=incoming.location,
                        language=incoming.language,
                        job_group=taxonomy.job_group,
                        employment_kind=taxonomy.employment_kind,
                        campus_cycle=taxonomy.campus_cycle,
                        lifecycle_status=next_status,
                        status_reason="source_declared_status",
                        description=incoming.description,
                        content_hash=digest,
                        metadata_json={**incoming.metadata, "published_at": incoming.published_at, "taxonomy_confidence": taxonomy.confidence},
                        first_seen_at=observed_at,
                        last_seen_at=observed_at,
                        last_verified_at=observed_at if next_status == "open" else None,
                        archived_at=observed_at if next_status == "historical" else None,
                    )
                    session.add(job)
                    session.flush()
                    created += 1
                    affected.add(job.id)
                    self._add_version(session, job, observed_at)
                    continue

                changed = job.content_hash != digest or job.lifecycle_status != next_status
                job.source_url = incoming.source_url
                job.company = incoming.company
                job.company_key = _company_key(incoming.company)
                job.title = incoming.title
                job.location = incoming.location
                job.language = incoming.language
                job.job_group = taxonomy.job_group
                job.employment_kind = taxonomy.employment_kind
                job.campus_cycle = taxonomy.campus_cycle
                job.description = incoming.description
                job.content_hash = digest
                job.metadata_json = {**incoming.metadata, "published_at": incoming.published_at, "taxonomy_confidence": taxonomy.confidence}
                job.lifecycle_status = next_status
                job.status_reason = "source_declared_status"
                job.last_seen_at = observed_at
                job.missing_sync_count = 0
                job.archived_at = observed_at if next_status == "historical" else None
                if next_status == "open":
                    job.last_verified_at = observed_at
                if changed:
                    updated += 1
                    affected.add(job.id)
                    self._add_version(session, job, observed_at)
                else:
                    unchanged += 1

            if authoritative:
                stale = session.scalars(
                    select(JobRecord).where(
                        JobRecord.source_name.in_(source_names),
                        JobRecord.lifecycle_status.in_(("open", "missing")),
                        JobRecord.last_seen_at < observed_at,
                    )
                ).all()
                for job in stale:
                    job.missing_sync_count += 1
                    if job.missing_sync_count >= missing_threshold:
                        job.lifecycle_status = "historical"
                        job.status_reason = "missing_from_authoritative_source"
                        job.archived_at = observed_at
                        archived += 1
                    else:
                        job.lifecycle_status = "missing"
                        job.status_reason = "missing_once"
                    affected.add(job.id)
                    self._add_version(session, job, observed_at)
        return SyncStats(
            source_name=source_name,
            fetched=len(materialized),
            created=created,
            updated=updated,
            unchanged=unchanged,
            archived=archived,
            affected_ids=tuple(sorted(affected)),
        )

    @staticmethod
    def _add_version(session: Session, job: JobRecord, seen_at: datetime) -> None:
        session.add(
            JobVersion(
                job_id=job.id,
                content_hash=job.content_hash,
                lifecycle_status=job.lifecycle_status,
                snapshot_json=job_to_dict(job),
                seen_at=seen_at,
            )
        )

    def get(self, job_id: str) -> JobRecord | None:
        with self.sessions() as session:
            return session.get(JobRecord, job_id)

    def get_many(self, job_ids: Iterable[str]) -> list[JobRecord]:
        ids = list(job_ids)
        if not ids:
            return []
        with self.sessions() as session:
            return session.scalars(select(JobRecord).where(JobRecord.id.in_(ids))).all()

    def jobs_for_index(self) -> list[JobRecord]:
        with self.sessions() as session:
            return session.scalars(select(JobRecord).where(JobRecord.lifecycle_status != "missing")).all()

    def reclassify_job_groups(self, *, observed_at: datetime | None = None) -> tuple[str, ...]:
        """Backfill role-family fixes while preserving an auditable version trail."""
        when = observed_at or utcnow()
        changed: list[str] = []
        with self.sessions.begin() as session:
            rows = session.scalars(select(JobRecord)).all()
            for job in rows:
                next_group = classify_job(job.title, job.description).job_group
                if job.job_group == next_group:
                    continue
                job.job_group = next_group
                self._add_version(session, job, when)
                changed.append(job.id)
        return tuple(changed)
    def restore_snapshot_records_for_verification(
        self,
        source_names: Iterable[str],
        *,
        archived_reason: str = "snapshot_not_independently_verified",
        observed_at: datetime | None = None,
    ) -> tuple[str, ...]:
        """Restore prior snapshot archives to an honest, processable verification queue."""
        names = tuple(dict.fromkeys(name for name in source_names if name))
        if not names:
            return ()
        when = observed_at or utcnow()
        changed: list[str] = []
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(JobRecord).where(
                    JobRecord.source_name.in_(names),
                    JobRecord.lifecycle_status == "historical",
                    JobRecord.status_reason == archived_reason,
                )
            ).all()
            for job in rows:
                job.lifecycle_status = "unverified"
                job.status_reason = "awaiting_official_verification"
                job.archived_at = None
                self._add_version(session, job, when)
                changed.append(job.id)
        return tuple(changed)

    def apply_official_verification(
        self,
        *,
        verified_open_ids: Iterable[str],
        verified_closed_ids: Iterable[str],
        provider: str,
        observed_at: datetime | None = None,
    ) -> dict[str, int]:
        """Apply definitive results returned by an employer's public ATS API."""
        open_ids = tuple(dict.fromkeys(verified_open_ids))
        closed_ids = tuple(dict.fromkeys(job_id for job_id in verified_closed_ids if job_id not in set(open_ids)))
        when = observed_at or utcnow()
        updated_open = updated_closed = 0
        with self.sessions.begin() as session:
            if open_ids:
                rows = session.scalars(select(JobRecord).where(JobRecord.id.in_(open_ids))).all()
                for job in rows:
                    job.lifecycle_status = "open"
                    job.status_reason = f"official_{provider}_verified_open"
                    job.last_seen_at = when
                    job.last_verified_at = when
                    job.archived_at = None
                    self._add_version(session, job, when)
                    updated_open += 1
            if closed_ids:
                rows = session.scalars(select(JobRecord).where(JobRecord.id.in_(closed_ids))).all()
                for job in rows:
                    job.lifecycle_status = "historical"
                    job.status_reason = f"official_{provider}_not_listed"
                    job.archived_at = when
                    self._add_version(session, job, when)
                    updated_closed += 1
        return {"open": updated_open, "closed": updated_closed}

    def mark_verification_pending(self, job_ids: Iterable[str], *, reason: str, observed_at: datetime | None = None) -> int:
        """Record why a target remains unverified without presenting it as live."""
        ids = tuple(dict.fromkeys(job_ids))
        if not ids:
            return 0
        when = observed_at or utcnow()
        updated = 0
        with self.sessions.begin() as session:
            rows = session.scalars(select(JobRecord).where(JobRecord.id.in_(ids), JobRecord.lifecycle_status == "unverified")).all()
            for job in rows:
                if job.status_reason == reason:
                    continue
                job.status_reason = reason
                self._add_version(session, job, when)
                updated += 1
        return updated
    def archive_unverifiable_snapshot_sources(
        self,
        source_names: Iterable[str],
        *,
        reason: str = "snapshot_not_independently_verified",
        observed_at: datetime | None = None,
    ) -> tuple[str, ...]:
        """Move non-authoritative snapshot records out of the verification queue.

        A historical import has no authoritative absence signal, so retaining it
        as ``unverified`` indefinitely is misleading.  It remains searchable as
        historical market research and gains an auditable lifecycle version.
        """
        names = tuple(dict.fromkeys(name for name in source_names if name))
        if not names:
            return ()
        when = observed_at or utcnow()
        changed: list[str] = []
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(JobRecord).where(
                    JobRecord.source_name.in_(names),
                    JobRecord.lifecycle_status == "unverified",
                )
            ).all()
            for job in rows:
                job.lifecycle_status = "historical"
                job.status_reason = reason
                job.archived_at = when
                self._add_version(session, job, when)
                changed.append(job.id)
        return tuple(changed)
    def purge_historical(self, retention_days: int, *, now: datetime | None = None) -> int:
        cutoff = (now or utcnow()) - timedelta(days=retention_days)
        with self.sessions.begin() as session:
            result = session.execute(
                delete(JobRecord).where(
                    JobRecord.lifecycle_status == "historical", JobRecord.archived_at.is_not(None), JobRecord.archived_at < cutoff
                )
            )
            return int(result.rowcount or 0)

    def overview(self) -> dict[str, Any]:
        with self.sessions() as session:
            by_status = dict(session.execute(select(JobRecord.lifecycle_status, func.count()).group_by(JobRecord.lifecycle_status)).all())
            by_cycle = dict(session.execute(select(JobRecord.campus_cycle, func.count()).group_by(JobRecord.campus_cycle)).all())
            by_source = dict(session.execute(select(JobRecord.source_name, func.count()).group_by(JobRecord.source_name)).all())
            total = session.scalar(select(func.count()).select_from(JobRecord)) or 0
        return {"total_jobs": total, "by_status": by_status, "by_cycle": by_cycle, "by_source": by_source}

    def source_health(self) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(select(SourceHealth).order_by(SourceHealth.source_name)).all()
            return [
                {
                    "source_name": row.source_name,
                    "last_attempt_at": row.last_attempt_at.isoformat(),
                    "last_success_at": row.last_success_at.isoformat() if row.last_success_at else None,
                    "consecutive_failures": row.consecutive_failures,
                    "last_error": row.last_error,
                    "last_record_count": row.last_record_count,
                }
                for row in rows
            ]
