# CareerAgent 通用岗位模式

该模式不把项目定位为“大模型岗位助手”。它覆盖技术、产品、数据、运营、销售、职能等求职方向，并将检索结果明确分为两类：

- `public_jd`：从公开公司招聘页采集的具体岗位。可在采集日用于浏览和准备，但职位是否仍开放必须回到原页确认。
- `job_family_profile`：从 BOSS 公开聚合页或职业分类归纳的岗位画像。它只用于选方向、改简历、出面试题，**不能**被表述为某家公司当前在招，也不应该直接投递。

## 运行

在 `D:\mygit\multi-agent-rag-customer-support`：

```powershell
.\.venv\Scripts\python.exe -m career_agent.universal_cli summary
.\.venv\Scripts\python.exe -m career_agent.universal_cli index
.\.venv\Scripts\python.exe -m career_agent.universal_cli search "有 SQL、Python 和看板项目的数据分析应届生" --actionable-only
.\.venv\Scripts\uvicorn.exe career_agent.universal_asgi:app --port 8003
```

API：

- `GET /api/catalog/summary`：显示总量、岗位族和数据类型。
- `GET /api/records?artifact_type=public_jd`：只列出具体公开岗位。
- `GET /api/records/search?query=...&actionable_only=true`：语义检索且排除岗位画像。
- `POST /api/match`：对任意岗位族进行可解释能力匹配。请求体为 `{"resume_text":"...","record_id":"..."}`。

匹配分数是词表覆盖度，不是录用概率。项目会返回命中能力、缺口、证据和补强建议，并对岗位画像给出边界提示。

## 扩展数据的规范

1. 优先加公司官方招聘页，并保存 URL、采集日、职位状态说明。
2. BOSS 等聚合站的内容只能作为 `job_family_profile` 或明确标记的 `public_listing_snapshot`；不要伪装成单一公司 JD。
3. 任何自动化抓取前都应检查站点条款、robots、登录和频率限制。本项目当前是人工审阅公开结果后录入的版本化样本。
4. 每次新增来源后运行 `index`，并在测试中验证 ID、来源和 `live_vacancy` 字段。
