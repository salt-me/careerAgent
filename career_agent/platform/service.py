"""FastAPI API and lightweight management console for the lifecycle platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Iterable

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..universal_matching import build_universal_match
from .config import PlatformSettings
from .connectors import JobConnector
from .orchestration import DailySyncScheduler, SyncOrchestrator
from .quality import quality_report
from .repository import JobRepository, job_to_dict
from .taxonomy import cycle_guidance
from .vector_store import LifecycleVectorStore


class MatchRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=40_000)
    job_id: str = Field(min_length=1)


@dataclass
class PlatformComponents:
    settings: PlatformSettings
    repository: JobRepository
    vector_store: LifecycleVectorStore
    orchestrator: SyncOrchestrator
    scheduler: DailySyncScheduler | None = None


def _dashboard_html() -> str:
    return """<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>CareerAgent 管理后台</title>
<style>body{font:15px system-ui;margin:32px;background:#f7f8fb;color:#20242c}h1{margin:0 0 8px}section{background:#fff;border-radius:12px;padding:20px;margin:16px 0;box-shadow:0 1px 3px #0001}pre{white-space:pre-wrap;word-break:break-word}button{padding:8px 12px;border:0;border-radius:7px;background:#1667ff;color:#fff;cursor:pointer}</style>
</head><body><h1>CareerAgent 数据管理</h1><p>实时岗位、历史参考和来源健康状态。</p>
<section><button onclick='syncAll()'>立即同步已配置来源</button><pre id='overview'>加载中…</pre></section>
<section><h2>来源健康</h2><pre id='health'>加载中…</pre></section>
<script>async function load(){let a=await fetch('/api/admin/overview');document.querySelector('#overview').textContent=JSON.stringify(await a.json(),null,2);let b=await fetch('/api/admin/sources');document.querySelector('#health').textContent=JSON.stringify(await b.json(),null,2)} async function syncAll(){let r=await fetch('/api/admin/sync',{method:'POST'});alert(JSON.stringify(await r.json()));load()} load()</script></body></html>"""


def create_platform_app(components: PlatformComponents) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        components.repository.create_schema()
        if components.settings.scheduler_enabled and components.scheduler:
            components.scheduler.start()
        yield
        if components.scheduler:
            components.scheduler.shutdown()

    app = FastAPI(title="CareerAgent Lifecycle Platform", version="2.0.0", lifespan=lifespan)

    def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
        token = components.settings.admin_token
        if token and x_admin_token != token:
            raise HTTPException(status_code=401, detail="Invalid admin token")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "database_backend": "postgresql" if components.settings.is_postgres() else "sqlite_local_demo",
            "scheduler_enabled": components.settings.scheduler_enabled,
            **components.repository.overview(),
        }

    @app.get("/admin", response_class=HTMLResponse)
    def admin() -> str:
        return _dashboard_html()

    @app.get("/api/admin/overview")
    def admin_overview() -> dict[str, Any]:
        return {"overview": components.repository.overview(), "quality": quality_report(components.repository)["checks"]}

    @app.get("/api/admin/sources")
    def admin_sources() -> list[dict[str, Any]]:
        return components.repository.source_health()

    @app.post("/api/admin/sync")
    def sync_all(x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        require_admin(x_admin_token)
        return {"results": [result.to_dict() for result in components.orchestrator.sync_all()]}

    @app.post("/api/admin/sync/{source_name}")
    def sync_source(source_name: str, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        require_admin(x_admin_token)
        if source_name not in components.orchestrator.connectors:
            raise HTTPException(status_code=404, detail="Configured source not found")
        return components.orchestrator.sync_one(source_name).to_dict()

    @app.get("/api/data-quality")
    def data_quality() -> dict[str, Any]:
        return quality_report(components.repository)

    @app.get("/api/jobs/search")
    def search_jobs(
        query: str = Query(min_length=2, max_length=2_000),
        scope: str = Query(default="live", pattern="^(live|history|all)$"),
        limit: int = Query(default=10, ge=1, le=50),
        campus_cycle: str | None = None,
        employment_kind: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            hit.to_dict()
            for hit in components.vector_store.search(
                query, scope=scope, limit=limit, campus_cycle=campus_cycle, employment_kind=employment_kind
            )
        ]

    @app.post("/api/jobs/match")
    def match_job(payload: MatchRequest) -> dict[str, Any]:
        job = components.repository.get(payload.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        record = job_to_dict(job)
        match_record = {**record, "job_family": job.job_group, "live_vacancy": job.lifecycle_status == "open"}
        return {
            "job": {key: value for key, value in record.items() if key != "text"},
            "match": build_universal_match(payload.resume_text, match_record).to_dict(),
            "cycle_guidance": cycle_guidance(job.campus_cycle, job.employment_kind),
            "application_notice": "可直接投递" if job.lifecycle_status == "open" else "历史或未验证记录，仅作参考；请先访问来源链接确认。",
        }

    return app

