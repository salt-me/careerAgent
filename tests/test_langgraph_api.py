from __future__ import annotations

from fastapi.testclient import TestClient

from career_agent.asgi import app
from career_agent.langgraph_flow import run_langgraph_workflow


RESUME = "我使用 Python、RAG 和 Docker 完成知识库问答项目，并为检索链路写了评测脚本。"
JD = "岗位要求：熟悉 Python、RAG 和评测。加分项：熟悉 LangGraph。"


def test_langgraph_routes_to_interview_then_critic() -> None:
    result = run_langgraph_workflow(RESUME, JD, route="interview")
    assert [entry["node"] for entry in result.trace] == [
        "input_validation",
        "match_agent",
        "interview_agent",
        "critic",
        "workflow",
    ]
    assert result.critic and result.critic.passed


def test_fastapi_exposes_match_and_feedback() -> None:
    client = TestClient(app)
    response = client.post("/api/match", json={"resume_text": RESUME, "jd_text": JD})
    assert response.status_code == 200
    assert response.json()["critic"]["passed"] is True
    feedback = client.post("/api/feedback", json={"request_id": response.json()["request_id"], "helpful": True})
    assert feedback.status_code == 202
