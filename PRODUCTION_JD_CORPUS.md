# CareerAgent 生产 JD 语料

生产语料由两层组成：

- 10,000 条带公司、职位、ATS 链接与 CC0 许可的 Open Jobs 快照；
- 牛客公开招聘专场的历史职位摘要。导入器保留每个公开 `jobIds`、公司和源页面链接；其状态统一标为 `closed`，不会作为实时职位推荐。

运行：

```powershell
.\.venv\Scripts\python.exe -m career_agent.production_corpus_cli
.\.venv\Scripts\python.exe -c "from career_agent.production_vector_store import ProductionJobVectorStore; print(ProductionJobVectorStore().rebuild())"
uvicorn career_agent.production_asgi:app --port 8000
```

每次启动和 `/api/corpus/report` 都会给出总量、岗位大类的不同公司数、来源分布和中文平台批次摘要。每个岗位大类需满足至少 10 家不同公司的约束；岗位大类采用上游结构化 function，中文平台的招聘方向映射到同一稳定分类。
