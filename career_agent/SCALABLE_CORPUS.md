# 10,000 条 JD 语料管线

这个模块是面向大规模语料的入口，不用人工伪造记录来“凑满” 10,000 条。

## 数据契约

将人工审阅后的公开页面摘要放入 `career_agent/data/external_sources/` 的 `.json` 或 `.jsonl` 文件。每条必须包含：

```json
{
  "source_name": "liepin | nowcoder | baidu | xiaohongshu | boss | official_company",
  "source_url": "https://...",
  "title": "职位标题",
  "company": "公司名",
  "location": "城市",
  "text": "从公开页人工概括的职责和要求，至少 40 字",
  "captured_at": "2026-08-02",
  "source_status": "open | closed | unknown"
}
```

可选字段：`source_job_id`、`position`、`job_family`、`experience`、`employment_type`、`published_at`、`source_note`。

`source_status=closed` 的历史职位可以用于技能趋势检索，但不会被标为在招；投递功能应只筛选 `open`。

## 质量门槛

- 目标：10,000 条去重后的 `public_jd`。
- 每个规范化岗位至少来自 10 家不同公司；使用公司标准化名称计算，不能用同一公司重复发布凑数。
- 每条保留来源 URL、来源平台、采集日和状态。缺字段、无效 URL、短摘要会被拒绝。
- 按 `source_url` 和 `(公司、规范化岗位、城市)` 去重。

运行：

```powershell
.\.venv\Scripts\python.exe -m career_agent.scalable_cli report
.\.venv\Scripts\python.exe -c "from career_agent.bulk_vector_store import BulkJobVectorStore; print(BulkJobVectorStore().rebuild())"
```

分批嵌入和分批 Qdrant upsert 默认分别为 128、256；这使 10,000 条规模不会一次性堆入向量化请求或写入请求。遵守各平台条款、robots、登录限制和频率限制；当前仓库只接收人工复核后的公开摘要或有授权的数据导出。
