# 扩展公开 JD 语料（推荐入口）

当前推荐的扩展语料位于 `data/public_jds_expanded.json`，共 **12 条**：

- 大模型应用、基座研发、文本生成、搜索优化；
- Agent 平台、Agentic RAG、AI Coding、产研效能 Agent；
- 大模型训练 Infra 与模型部署相关工程能力。

每条记录都保存官方页面 URL 与抓取日期。`published_at=not_disclosed` 表示页面搜索结果没有提供可核验的发布日期，不能将其当成职位发布时间。

```powershell
.\.venv\Scripts\python.exe -m career_agent.curated_cli index
.\.venv\Scripts\python.exe -m career_agent.curated_cli search "Python RAG Agent 校招"
.\.venv\Scripts\python.exe -m uvicorn career_agent.curated_asgi:app --host 127.0.0.1 --port 8002
```

接口：

- `GET /api/jds`：浏览语料与来源；
- `GET /api/jds/search?query=...`：Qdrant 语义检索；
- `POST /api/jds/match`：将 `job_id` 对应的公开 JD 输入 CareerAgent 的 LangGraph 工作流。

这个集合作为求职方向分析的初始语料，而不是职位聚合器。每次投递前都需要跳转来源页面确认岗位仍然开放。
