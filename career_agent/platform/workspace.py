"""Personal, local-first job tracking persisted alongside the platform DB."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkspaceBase(DeclarativeBase):
    pass


class SavedJob(WorkspaceBase):
    __tablename__ = "career_saved_jobs"
    __table_args__ = (UniqueConstraint("profile_key", "job_id", name="uq_saved_profile_job"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_key: Mapped[str] = mapped_column(String(80), default="local")
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApplicationTrack(WorkspaceBase):
    __tablename__ = "career_application_tracks"
    __table_args__ = (UniqueConstraint("profile_key", "job_id", name="uq_application_profile_job"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_key: Mapped[str] = mapped_column(String(80), default="local")
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default="saved")
    note: Mapped[str] = mapped_column(Text, default="")
    target_date: Mapped[str | None] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class JobSubscription(WorkspaceBase):
    __tablename__ = "career_job_subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_key: Mapped[str] = mapped_column(String(80), default="local")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CareerProfile(WorkspaceBase):
    __tablename__ = "career_profiles"

    profile_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    target_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    campus_cycle: Mapped[str] = mapped_column(String(64), default="")
    employment_kind: Mapped[str] = mapped_column(String(32), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class SubscriptionDelivery(WorkspaceBase):
    __tablename__ = "career_subscription_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

class CareerWorkspace:
    """Storage abstraction that works with both SQLite and PostgreSQL URLs."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, future=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, future=True)

    def create_schema(self) -> None:
        WorkspaceBase.metadata.create_all(self.engine)

    @staticmethod
    def _profile(row: CareerProfile | None, profile_key: str) -> dict[str, Any]:
        if row is None:
            return {
                "profile_key": profile_key,
                "display_name": "",
                "email": "",
                "target_roles": [],
                "target_locations": [],
                "campus_cycle": "",
                "employment_kind": "",
                "updated_at": None,
            }
        return {
            "profile_key": row.profile_key,
            "display_name": row.display_name,
            "email": row.email,
            "target_roles": list(row.target_roles or []),
            "target_locations": list(row.target_locations or []),
            "campus_cycle": row.campus_cycle,
            "employment_kind": row.employment_kind,
            "updated_at": row.updated_at.isoformat(),
        }

    def profile(self, profile_key: str = "local") -> dict[str, Any]:
        with self.sessions() as session:
            return self._profile(session.get(CareerProfile, profile_key), profile_key)

    def update_profile(
        self,
        *,
        profile_key: str = "local",
        display_name: str = "",
        email: str = "",
        target_roles: list[str] | None = None,
        target_locations: list[str] | None = None,
        campus_cycle: str = "",
        employment_kind: str = "",
    ) -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.get(CareerProfile, profile_key)
            if row is None:
                row = CareerProfile(profile_key=profile_key)
                session.add(row)
            row.display_name = display_name.strip()[:120]
            row.email = email.strip()[:320]
            row.target_roles = [item.strip()[:120] for item in (target_roles or []) if item.strip()][:12]
            row.target_locations = [item.strip()[:120] for item in (target_locations or []) if item.strip()][:12]
            row.campus_cycle = campus_cycle.strip()[:64]
            row.employment_kind = employment_kind.strip()[:32]
            session.flush()
            return self._profile(row, profile_key)
    @staticmethod
    def _saved(row: SavedJob) -> dict[str, Any]:
        return {"job_id": row.job_id, "note": row.note, "created_at": row.created_at.isoformat()}

    def save_job(self, job_id: str, note: str = "", profile_key: str = "local") -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.scalar(select(SavedJob).where(SavedJob.profile_key == profile_key, SavedJob.job_id == job_id))
            if row is None:
                row = SavedJob(profile_key=profile_key, job_id=job_id, note=note[:4000])
                session.add(row)
                session.flush()
            elif note:
                row.note = note[:4000]
            return self._saved(row)

    def remove_saved_job(self, job_id: str, profile_key: str = "local") -> bool:
        with self.sessions.begin() as session:
            row = session.scalar(select(SavedJob).where(SavedJob.profile_key == profile_key, SavedJob.job_id == job_id))
            if row is None:
                return False
            session.delete(row)
            return True

    def saved_jobs(self, profile_key: str = "local") -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(select(SavedJob).where(SavedJob.profile_key == profile_key).order_by(SavedJob.created_at.desc())).all()
            return [self._saved(row) for row in rows]

    def track_application(self, job_id: str, stage: str, note: str = "", target_date: str | None = None, profile_key: str = "local") -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.scalar(select(ApplicationTrack).where(ApplicationTrack.profile_key == profile_key, ApplicationTrack.job_id == job_id))
            if row is None:
                row = ApplicationTrack(profile_key=profile_key, job_id=job_id, stage=stage, note=note[:4000], target_date=target_date)
                session.add(row)
                session.flush()
            else:
                row.stage, row.note, row.target_date = stage, note[:4000], target_date
            return {"job_id": row.job_id, "stage": row.stage, "note": row.note, "target_date": row.target_date, "updated_at": row.updated_at.isoformat()}

    def applications(self, profile_key: str = "local") -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(select(ApplicationTrack).where(ApplicationTrack.profile_key == profile_key).order_by(ApplicationTrack.updated_at.desc())).all()
            return [{"job_id": row.job_id, "stage": row.stage, "note": row.note, "target_date": row.target_date, "updated_at": row.updated_at.isoformat()} for row in rows]

    def create_subscription(self, name: str, query: str, filters: dict[str, Any] | None = None, profile_key: str = "local") -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = JobSubscription(profile_key=profile_key, name=name[:120], query=query[:500], filters=filters or {})
            session.add(row)
            session.flush()
            return {"id": row.id, "name": row.name, "query": row.query, "filters": row.filters, "active": row.active, "created_at": row.created_at.isoformat()}

    def subscriptions(self, profile_key: str = "local") -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(select(JobSubscription).where(JobSubscription.profile_key == profile_key).order_by(JobSubscription.created_at.desc())).all()
            return [{"id": row.id, "name": row.name, "query": row.query, "filters": row.filters, "active": row.active, "created_at": row.created_at.isoformat()} for row in rows]
    def subscription(self, subscription_id: int, profile_key: str = "local") -> dict[str, Any] | None:
        with self.sessions() as session:
            row = session.scalar(select(JobSubscription).where(JobSubscription.id == subscription_id, JobSubscription.profile_key == profile_key))
            if row is None:
                return None
            return {"id": row.id, "name": row.name, "query": row.query, "filters": row.filters, "active": row.active, "created_at": row.created_at.isoformat()}

    def record_subscription_delivery(self, *, profile_key: str, subscription_id: int, recipient: str | None, status: str, matched_count: int, detail: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = SubscriptionDelivery(profile_key=profile_key, subscription_id=subscription_id, recipient=recipient, status=status[:32], matched_count=max(0, matched_count), detail=detail[:4000])
            session.add(row)
            session.flush()
            return {"id": row.id, "subscription_id": row.subscription_id, "recipient": row.recipient, "status": row.status, "matched_count": row.matched_count, "detail": row.detail, "created_at": row.created_at.isoformat()}

    def active_subscription_targets(self) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.execute(select(JobSubscription, CareerProfile).outerjoin(CareerProfile, JobSubscription.profile_key == CareerProfile.profile_key).where(JobSubscription.active.is_(True))).all()
            return [
                {
                    "profile_key": subscription.profile_key,
                    "email": profile.email if profile else "",
                    "subscription": {"id": subscription.id, "name": subscription.name, "query": subscription.query, "filters": subscription.filters, "active": subscription.active, "created_at": subscription.created_at.isoformat()},
                }
                for subscription, profile in rows
            ]
