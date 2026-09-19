"""Zero-dependency JSON API and browser demo for CareerAgent."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .workflow import CareerWorkflow


PAGE = """<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>CareerAgent</title><style>
body{margin:0;background:#f7f8fc;color:#162033;font:15px system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}main{max-width:1120px;margin:32px auto;padding:0 20px}h1{margin-bottom:4px}.sub{color:#586174;margin-top:0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{background:white;border:1px solid #e4e8f0;border-radius:12px;padding:18px;box-shadow:0 2px 10px #1b2b4d0a}textarea{width:100%;box-sizing:border-box;min-height:270px;border:1px solid #cbd3e1;border-radius:8px;padding:10px;font:14px ui-monospace,monospace;resize:vertical}button{background:#315efb;color:white;border:0;border-radius:8px;padding:10px 14px;font-weight:650;cursor:pointer;margin:16px 8px 0 0}button.secondary{background:#edf1ff;color:#294ac9}pre{white-space:pre-wrap;word-break:break-word;min-height:180px;background:#111827;color:#e5e7eb;padding:14px;border-radius:8px;overflow:auto}@media(max-width:760px){.grid{grid-template-columns:1fr}main{margin-top:18px}}</style></head>
<body><main><h1>CareerAgent</h1><p class=\"sub\">有证据链的岗位匹配与面试准备 · 本地演示版</p><div class=\"grid\"><section class=\"card\"><h2>匿名简历</h2><textarea id=\"resume\"></textarea></section><section class=\"card\"><h2>岗位 JD</h2><textarea id=\"jd\"></textarea></section></div><button onclick=\"run('match')\">生成岗位匹配</button><button class=\"secondary\" onclick=\"run('interview')\">生成面试准备</button><section class=\"card\"><h2>结果（含 trace 与 Critic）</h2><pre id=\"output\">点击按钮开始分析。</pre></section></main><script>
const resume=`计算机科学与技术专业本科生。熟悉 Python、SQL、Git 和 Linux，完成过机器学习、深度学习课程项目。\n个人项目：使用 Python 实现文档知识库问答原型，完成文本清洗、关键词检索和结果引用展示；使用 Docker Compose 配置本地服务。\n正在系统学习 Transformer、PyTorch、LLM、RAG 与 LangGraph，并记录检索评测实验。`;
const jd=`AI Agent 开发工程师（校招）\n岗位要求：熟悉 Python，掌握 LLM、RAG、向量检索与重排序的基本原理；具备 LangGraph 或 LangChain Agent 开发经验。\n加分项：熟悉 FastAPI、Docker、评测体系、PyTorch 或 Transformer；能够完成文档处理、检索链路优化和可维护的服务化交付。\n岗位职责：参与大模型应用的方案设计、实现、离线评测和迭代复盘。`;
document.querySelector('#resume').value=resume;document.querySelector('#jd').value=jd;
async function run(route){const output=document.querySelector('#output');output.textContent='分析中…';try{const response=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({resume_text:document.querySelector('#resume').value,jd_text:document.querySelector('#jd').value})});const payload=await response.json();output.textContent=JSON.stringify(payload,null,2)}catch(error){output.textContent='请求失败：'+error.message}}</script></body></html>"""


class CareerAgentHandler(BaseHTTPRequestHandler):
    workflow = CareerWorkflow()

    def _send(self, status: int, payload: dict | str, content_type: str = "application/json; charset=utf-8") -> None:
        body = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(HTTPStatus.OK, {"status": "ok", "service": "career-agent"})
        elif self.path == "/":
            self._send(HTTPStatus.OK, PAGE, "text/html; charset=utf-8")
        else:
            self._send(HTTPStatus.NOT_FOUND, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        route_by_path = {"/api/match": "match", "/api/interview": "interview"}
        route = route_by_path.get(self.path)
        if route is None:
            self._send(HTTPStatus.NOT_FOUND, {"detail": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 80_000:
                raise ValueError("输入超过 80,000 字节限制。")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self.workflow.run(payload.get("resume_text", ""), payload.get("jd_text", ""), route=route)
            self._send(HTTPStatus.OK, result.to_dict())
        except (ValueError, json.JSONDecodeError) as error:
            self._send(HTTPStatus.BAD_REQUEST, {"detail": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), CareerAgentHandler)
    print(f"CareerAgent 已启动：http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCareerAgent 已停止。")
    finally:
        server.server_close()
