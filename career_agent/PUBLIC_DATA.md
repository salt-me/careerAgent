# 公开 JD、Embedding 与 Qdrant 接入

## 语料边界

`data/public_jds.json` 初始收录 3 条可公开访问的官方职位页面，并保存 `source`、`published_at` 和 `captured_at`。本地只保存为检索而写的短摘要，原网页仍是唯一权威来源；投递或复用前应打开来源页面确认职位仍有效。

- 百度 2026 校招大模型算法工程师：[官方页面](https://talent.baidu.com/jobs/detail/GRADUATE/ccfdea4e-4ae4-4954-9062-fd94960a2861)
- 小红书 2026 校招大模型应用算法工程师：[官方页面](https://job.xiaohongshu.com/campus/position/17018?referer_code=EJOZXFQLXGQA)
- 小红书 AI 应用开发工程师：[官方页面](https://job.xiaohongshu.com/campus/position/18716)

## 本地向量链路

`BAAI/bge-small-zh-v1.5` 通过 FastEmbed 生成 512 维中文 embedding，Qdrant Local Mode 将向量持久化到已忽略的 `qdrant_storage/career_agent_public`。首次索引会下载约 96 MB 的公开模型权重；之后可离线检索。

```powershell
.\.venv\Scripts\python.exe -m career_agent.public_cli index
.\.venv\Scripts\python.exe -m career_agent.public_cli search "需要 RAG 和 Agent 工程经验的校招岗位"
.\.venv\Scripts\python.exe -m uvicorn career_agent.public_asgi:app --host 127.0.0.1 --port 8001
```

服务接口：

- `POST /api/public-jds/rebuild`：手动重建索引；
- `GET /api/public-jds/search?query=...`：语义搜索公开 JD；
- `POST /api/public-jds/match`：选择 `job_id` 后调用 CareerAgent LangGraph 流程，返回岗位来源与匹配/面试准备结果。

生产部署时将 Qdrant Local Mode 切换为独立 Qdrant 服务，并将更新过程放入审核后的定时任务；不要把未经允许的求职者简历写入公开向量库。
