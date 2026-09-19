# CareerAgent 10k 全岗位 JD 语料

该项目的主语料不是爬取 Boss、猎聘或牛客的受限页面，而是来自 [Open Jobs](https://github.com/elliottdehn/open-jobs) 的 CC0 公开快照。每条记录保留公司、职位、来源 ATS 链接、抓取日期和许可信息；`source_status` 统一为 `unknown`，因此不会把历史职位误标为仍在招聘。

导入时仅通过 HTTP Range 读取远端 Parquet 所需行组，不下载 21GB 原文件。主数据文件为 `career_agent/data/licensed_sources/open_jobs_cc0_10000.jsonl`，对应快照清单为 `career_agent/data/licensed_sources/open_jobs_cc0_10000.manifest.json`。

```powershell
.\.venv\Scripts\python.exe -m career_agent.verified_all_job_cli report
.\.venv\Scripts\python.exe -c "from career_agent.verified_all_job_vector_store import VerifiedAllJobVectorStore; print(VerifiedAllJobVectorStore().rebuild())"
uvicorn career_agent.verified_all_job_asgi:app --port 8000
```

报告按上游结构化 `function` 作为“岗位大类”（例如 engineering、data、sales、healthcare），逐类检查不同公司数是否不少于 10；不会将同一公司不同招聘链接的职位错误合并。现有中文公开样例保留为种子数据，并映射到同一岗位大类；它们只占很小比例，检索结果携带 `language` 与 `source_name`，前端可按需筛选。
