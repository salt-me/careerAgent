# 当前正式运行入口

使用以下入口启动完整的 CareerAgent 求职平台：

```powershell
.\.venv\Scripts\python.exe -m uvicorn career_agent.career_portal_complete_asgi:app --env-file .env.career-platform.local --host 127.0.0.1 --port 8000
```

`career_portal_web_v2_asgi` 和 `career_portal_asgi` 是保留的兼容入口。完整入口额外提供岗位类别筛选、精确重复簇总数、中国官网来源审核目录、TXT/DOCX 简历解析和订阅命中预览。
