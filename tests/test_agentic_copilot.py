from __future__ import annotations

import json

from career_agent.platform.agentic_copilot import AgentLLMSettings, ToolCallingCareerAgent
from career_agent.platform.career_copilot import CopilotRequest


class FakeResponsesTransport:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def create(self, payload: dict) -> dict:
        self.payloads.append(payload)
        if len(self.payloads) == 1:
            return {"output": [{"type": "function_call", "call_id": "call-search", "name": "search_jobs", "arguments": json.dumps({"query": "Python", "scope": "live", "campus_cycle": "", "employment_kind": "", "location": "", "limit": 3})}]}
        return {"output": [], "output_text": "已根据岗位工具结果生成建议。"}


def test_agent_uses_bounded_read_only_tools_and_returns_evidence(platform_components) -> None:
    transport = FakeResponsesTransport()
    agent = ToolCallingCareerAgent(platform_components.repository, platform_components.vector_store, settings=AgentLLMSettings(True, "test-key", "test-model", "https://api.example.test/v1", 10), transport=transport)
    plan = agent.plan(CopilotRequest(target_role="Python", resume_text="Python SQL"), use_llm=True)
    assert plan["mode"] == "llm_tool_calling"
    assert plan["agent"]["used_llm"] is True
    assert plan["agent"]["tool_calls"][0]["tool"] == "search_jobs"
    assert plan["citations"][0]["source_url"].startswith("https://jobs.example.test/")
    assert transport.payloads[0]["tool_choice"] == "required"
    assert transport.payloads[0]["max_output_tokens"] == 128
    assert transport.payloads[1]["input"][-1]["type"] == "function_call_output"


def test_agent_requires_per_request_consent_even_when_configured(platform_components) -> None:
    agent = ToolCallingCareerAgent(platform_components.repository, platform_components.vector_store, settings=AgentLLMSettings(True, "test-key", "test-model", "https://api.example.test/v1", 10), transport=FakeResponsesTransport())
    plan = agent.plan(CopilotRequest(target_role="Python"), use_llm=False)
    assert plan["mode"] == "grounded_career_copilot"
    assert plan["agent"]["reason"] == "external_llm_consent_not_given"


def test_ollama_provider_does_not_require_an_api_key(platform_components) -> None:
    transport = FakeResponsesTransport()
    settings = AgentLLMSettings(True, None, "qwen3:4b", "http://host.docker.internal:11434/v1", 10, "ollama")
    agent = ToolCallingCareerAgent(platform_components.repository, platform_components.vector_store, settings=settings, transport=transport)
    plan = agent.plan(CopilotRequest(target_role="Python"), use_llm=True)
    assert plan["agent"]["provider"] == "ollama"
    assert plan["agent"]["used_llm"] is True
