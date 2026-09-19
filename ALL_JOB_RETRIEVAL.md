# 多语种向量检索

`career_agent.multilingual_all_job_vector_store` 是 10k 全岗位语料的正式索引器。它为英文主语料和中文查询使用同一个多语种 embedding 空间，并将向量写入本地 Qdrant collection：`career_agent_all_jobs_10k_multilingual_v1`。

```powershell
.\.venv\Scripts\python.exe -c "from career_agent.multilingual_all_job_vector_store import MultilingualAllJobVectorStore; print(MultilingualAllJobVectorStore().rebuild())"
uvicorn career_agent.multilingual_all_job_asgi:app --port 8000
```

主要接口：

- `GET /health`：语料数量、岗位—公司覆盖和索引状态。
- `GET /api/corpus/report`：可审计覆盖报告。
- `GET /api/jobs/search?query=后端工程师&position=engineering`：语义检索，返回公司、原始 ATS URL、采集日期和摘要。
- `POST /api/jobs/match`：传入 `resume_text` 与 `job_id`，复用项目已有的简历—JD 匹配解释。

职位快照可能过期，因此检索响应的 `source_status` 在 CC0 批次中为 `unknown`；用户申请前必须以返回的原始 ATS 链接为准。
