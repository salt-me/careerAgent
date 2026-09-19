# CareerAgent 生命周期平台

平台把职位分为三个互不混淆的状态：

- `open`：由权威来源最近一次同步确认仍开放，进入实时 Qdrant collection；
- `historical`：来源明确关闭，或连续两次权威同步缺失，进入历史 collection；
- `unverified`：授权快照或人工审核历史页，供市场参考，不被标为可投递职位。

`missing` 是短暂保护状态：第一次从权威来源消失时不立即归档，避免单次网络故障误关职位。默认第二次连续缺失才归档。历史职位默认保留 1,095 天（3 年），每日同步后自动清理到期记录。

## 部署

```powershell
Copy-Item .env.career-platform.example .env.career-platform
docker compose -f docker-compose.career-platform.yml up --build
```

打开 `http://localhost:8000/admin` 查看来源健康、数据质量与同步入口。生产环境必须使用 PostgreSQL；本地 SQLite 只用于测试和试运行。

## 首次导入已审核历史语料

```powershell
python -m career_agent.platform_cli import-snapshot career_agent/data/licensed_sources/open_jobs_cc0_10000.jsonl career_agent/data/licensed_sources/nowcoder_careers_413_public.jsonl
python -m career_agent.platform_cli rebuild-index
```

## 每日同步

设置 `CAREER_AGENT_GREENHOUSE_BOARDS` 为已获授权或公开的 Greenhouse board token。系统每天按 `CAREER_AGENT_SCHEDULER_HOUR_UTC` 运行：新增和变更职位增量更新，连续缺失两次的职位进入历史库。对牛客、猎聘、Boss 等受限平台，只允许接入其授权 API、合作导出或人工审核批次，不能绕过登录、验证码或平台访问控制。
