# 生命周期平台运行手册

正式入口是 `career_agent.lifecycle_asgi:app`。它为所有配置的官方来源连接器应用三次指数退避重试；只有三次均失败才记录来源失败并保留现有职位状态。

```powershell
Copy-Item .env.career-platform.example .env.career-platform
docker compose -f docker-compose.lifecycle-platform.yml up --build
```

若不使用 Docker，本地试运行可执行：

```powershell
$env:CAREER_AGENT_GREENHOUSE_BOARDS='airtable'
$env:CAREER_AGENT_SCHEDULER_ENABLED='true'
uvicorn career_agent.lifecycle_asgi:app --port 8000
```

生产环境必须把 `CAREER_AGENT_DATABASE_URL` 配为 PostgreSQL。`/admin` 提供总量、数据质量、来源健康和手动同步入口；如配置 `CAREER_AGENT_ADMIN_TOKEN`，手动同步 API 必须携带 `X-Admin-Token`。
