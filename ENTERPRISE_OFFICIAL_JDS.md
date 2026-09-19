# 企业官网 / ATS 增强语料

新增批次 `official_ats_100plus_companies.jsonl` 来自 Open Jobs 的 CC0 快照，但每条记录保存的 `source_url` 是企业实际招聘系统的直接申请链接（例如 Greenhouse、Ashby、Lever、Workable 等），而非聚合页。

导入器会先读取当前生产语料的公司集合，再从后续行组中选择未出现过的企业；写入前强制验证至少 100 家净新增企业和有效 JD。对应 manifest 可审计来源、行组、许可、原始文件 ETag、企业数和 ATS 域名分布。

```powershell
.\.venv\Scripts\python.exe -m career_agent.official_ats_import_cli --row-group 3 --min-new-companies 100
.\.venv\Scripts\python.exe -m career_agent.enterprise_corpus_cli
```

这些记录的 `source_status` 均为 `unknown`，因为来源是快照；检索结果会保留直接 ATS URL，用户投递前必须访问原链接确认职位状态。
