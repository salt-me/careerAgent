# 授权 JD 数据导入

当通过平台的授权 API、合作方导出或自有招聘系统获得数据后，可将 CSV 作为一个不可变批次导入。不要使用本脚本绕过登录、反爬、robots 或平台条款。

CSV 至少需要这些列：`source_url,title,company,location,text,captured_at`。可选：`source_job_id,source_status,position,job_family,experience,employment_type,published_at,source_note`。

先只校验：

```powershell
.\.venv\Scripts\python.exe -m career_agent.source_import_cli D:\exports\nowcoder_jobs.csv --source-name nowcoder
```

没有任何拒绝行时，再显式写入批次：

```powershell
.\.venv\Scripts\python.exe -m career_agent.source_import_cli D:\exports\nowcoder_jobs.csv --source-name nowcoder --output career_agent\data\external_sources\nowcoder_export_20260802.jsonl
```

牛客企业服务公开说明其支持批量数据下载和开放 API 对接；这类授权导出是把语料扩展到 10,000 条的正确入口。猎聘或其他来源同样应只使用拥有权限的数据导出或人工复核的公开页面摘要。
