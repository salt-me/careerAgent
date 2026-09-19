# 当前正式入口（完整非 Docker 版）

```powershell
.\.venv\Scripts\python.exe -m uvicorn career_agent.career_portal_complete_asgi:app --env-file .env.career-platform.local --host 127.0.0.1 --port 8000
```

这个入口包含岗位检索、实时/历史索引、简历 TXT/DOCX 解析、匹配建议、收藏/投递追踪、订阅命中预览、数据质量和可插拔官方 JSON 源合同。
