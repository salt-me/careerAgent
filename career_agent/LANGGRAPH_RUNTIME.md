# CareerAgent 正式运行入口（LangGraph + FastAPI）

当前正式服务由 `career_agent/langgraph_flow.py` 和 `career_agent/asgi.py` 提供。其工作流包含：`input_validation -> match_agent -> (interview_agent) -> critic`；每次响应返回节点 trace 和时间。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-career-agent.txt
```

## 验证与运行

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn career_agent.asgi:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000` 使用页面，`http://127.0.0.1:8000/docs` 查看 OpenAPI 文档。

## 反馈数据边界

`POST /api/feedback` 仅接收长度受限的内存反馈，重启服务即清空。正式使用时应将脱敏反馈写入受权限控制的数据库，并提供删除机制。
