# CareerAgent：通用求职岗位匹配与面试准备系统

本仓库原始内容是客服 RAG 项目；本 fork 新增并完成的主项目在 `career_agent/`。CareerAgent 支持面向技术、产品、数据、运营、销售和职能岗位的检索、匹配、能力缺口与面试准备，而不仅是大模型岗位。

先读：

- [`career_agent/UNIVERSAL_CAREER_AGENT.md`](career_agent/UNIVERSAL_CAREER_AGENT.md)：通用模式、数据边界与 API。
- [`career_agent/RESUME_VERIFIED.md`](career_agent/RESUME_VERIFIED.md)：基于已经完成内容、可如实使用的简历表述。
- [`CAREER_AGENT.md`](CAREER_AGENT.md)：项目总体说明与本地运行入口。

最快验证：

```powershell
cd D:\mygit\multi-agent-rag-customer-support
.\.venv\Scripts\python.exe -m career_agent.universal_cli summary
.\.venv\Scripts\python.exe -m career_agent.universal_cli index
.\.venv\Scripts\python.exe -m career_agent.universal_cli search "有 SQL、Python、Excel 和看板项目的数据分析应届生" --actionable-only
.\.venv\Scripts\uvicorn.exe career_agent.universal_asgi:app --port 8003
```

数据原则：`public_jd` 才是具体公开职位，`job_family_profile` 仅为职业探索和简历准备而设；页面状态随时可能变化，投递前须回到原始招聘页确认。
