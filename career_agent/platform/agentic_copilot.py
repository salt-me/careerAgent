"""Opt-in, bounded LLM tool calling for CareerAgent.

The model can read only local versioned jobs through four tools.  It receives
no write/apply/delete tool, and failures fall back to the deterministic copilot.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .career_copilot import CareerCopilot, CopilotRequest
from .career_intelligence import build_match_insight, hybrid_rerank
from .repository import JobRepository, job_to_dict
from .vector_store import LifecycleVectorStore


@dataclass(frozen=True)
class AgentLLMSettings:
    enabled: bool
    api_key: str | None
    model: str
    base_url: str
    timeout_seconds: int
    provider: str = "openai"
    max_output_tokens: int = 128

    @classmethod
    def from_env(cls) -> "AgentLLMSettings":
        return cls(
            os.getenv("CAREER_AGENT_LLM_ENABLED", "false").strip().casefold() in {"1", "true", "yes", "on"},
            os.getenv("OPENAI_API_KEY") or None,
            os.getenv("CAREER_AGENT_LLM_MODEL", "career-qwen3:4b"),
            os.getenv("CAREER_AGENT_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            max(5, min(int(os.getenv("CAREER_AGENT_LLM_TIMEOUT_SECONDS", "45")), 120)),
            os.getenv("CAREER_AGENT_LLM_PROVIDER", "openai").strip().casefold() or "openai",
            max(64, min(int(os.getenv("CAREER_AGENT_LLM_MAX_OUTPUT_TOKENS", "128")), 2048)),
        )


class ResponsesTransport(Protocol):
    def create(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class OpenAIResponsesTransport:
    """Small Responses client for OpenAI-compatible providers.

    Ollama implements the non-stateful ``/v1/responses`` endpoint locally, so it
    can reuse the same bounded tool loop without an API key or a new SDK.
    """

    def __init__(self, settings: AgentLLMSettings) -> None:
        self.settings = settings

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        local_ollama = self.settings.provider == "ollama"
        if not local_ollama and not self.settings.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        request = urllib.request.Request(
            f"{self.settings.base_url}/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"Responses API HTTP {error.code}") from error
        except urllib.error.URLError as error:
            raise RuntimeError("Responses API unavailable") from error


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function", "name": name, "description": description, "strict": True,
        "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False},
    }


TOOL_SPECS = [
    _tool("search_jobs", "Search local versioned jobs and return official links only.", {
        "query": {"type": "string"}, "scope": {"type": "string", "enum": ["live", "history", "all"]},
        "campus_cycle": {"type": "string"}, "employment_kind": {"type": "string"}, "location": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
    }, ["query", "scope", "campus_cycle", "employment_kind", "location", "limit"]),
    _tool("get_job_details", "Read details of job IDs returned by search_jobs before recommending a specific job.", {
        "job_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
    }, ["job_ids"]),
    _tool("analyze_resume_for_jobs", "Compare supplied resume text with returned job IDs. It is preparation guidance, not a hiring prediction.", {
        "resume_text": {"type": "string"}, "job_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
    }, ["resume_text", "job_ids"]),
    _tool("get_source_freshness", "Read source health and verification timestamps for returned job IDs.", {
        "job_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 10},
    }, ["job_ids"]),
]


class ToolCallingCareerAgent:
    max_rounds = 4
    max_calls = 8

    def __init__(self, repository: JobRepository, vector_store: LifecycleVectorStore, *, settings: AgentLLMSettings | None = None, transport: ResponsesTransport | None = None) -> None:
        self.repository, self.vector_store = repository, vector_store
        self.settings = settings or AgentLLMSettings.from_env()
        self.transport = transport or OpenAIResponsesTransport(self.settings)
        self.fallback = CareerCopilot(repository, vector_store)
        self.evidence: dict[str, dict[str, Any]] = {}

    def _scoped_records(self, scope: str) -> list[dict[str, Any]]:
        rows = [job_to_dict(item) for item in self.repository.jobs_for_index()]
        if scope == "live": return [item for item in rows if item["lifecycle_status"] == "open"]
        if scope == "history": return [item for item in rows if item["lifecycle_status"] != "open"]
        return rows

    def _search_jobs(self, args: dict[str, Any]) -> dict[str, Any]:
        query, scope = str(args["query"]).strip(), str(args["scope"])
        rows = self._scoped_records(scope)
        cycle, kind, location = str(args["campus_cycle"]).strip(), str(args["employment_kind"]).strip(), str(args["location"]).casefold().strip()
        rows = [item for item in rows if (not cycle or item.get("campus_cycle") == cycle) and (not kind or item.get("employment_kind") == kind) and (not location or location in str(item.get("location", "")).casefold())]
        scores: dict[str, float] = {}
        try:
            hits = self.vector_store.search(query, scope=scope, limit=100, campus_cycle=cycle or None, employment_kind=kind or None)
            scores = {hit.id: hit.score for hit in hits}
            recalled = {item.id: job_to_dict(item) for item in self.repository.get_many(scores)}
            rows = [recalled[item_id] for item_id in scores if item_id in recalled and recalled[item_id] in rows]
        except Exception:
            pass
        jobs = []
        for item in hybrid_rerank(query, rows, scores)[:int(args["limit"])]:
            evidence = {"job_id": item["id"], "company": item["company"], "title": item["title"], "location": item["location"], "status": item["lifecycle_status"], "source_url": item["source_url"], "last_verified_at": item.get("last_verified_at"), "excerpt": item.get("excerpt", ""), "match_score": item.get("ranking", {}).get("score")}
            self.evidence[item["id"]] = evidence
            jobs.append(evidence)
        return {"query": query, "scope": scope, "jobs": jobs}

    def _get_job_details(self, args: dict[str, Any]) -> dict[str, Any]:
        jobs = []
        for record in self.repository.get_many(args["job_ids"]):
            item = job_to_dict(record)
            self.evidence[item["id"]] = {**self.evidence.get(item["id"], {}), "job_id": item["id"], "company": item["company"], "title": item["title"], "location": item["location"], "status": item["lifecycle_status"], "source_url": item["source_url"]}
            jobs.append({"job_id": item["id"], "company": item["company"], "title": item["title"], "campus_cycle": item["campus_cycle"], "employment_kind": item["employment_kind"], "status": item["lifecycle_status"], "source_url": item["source_url"], "description": item["text"][:6000]})
        return {"jobs": jobs}

    def _analyze_resume(self, args: dict[str, Any]) -> dict[str, Any]:
        analyses = []
        for record in self.repository.get_many(args["job_ids"]):
            item = job_to_dict(record)
            analyses.append({"job_id": item["id"], "company": item["company"], "title": item["title"], **build_match_insight(str(args["resume_text"]), item).to_dict()})
        return {"analyses": analyses, "boundary": "Preparation guidance only; not a hiring probability."}

    def _source_freshness(self, args: dict[str, Any]) -> dict[str, Any]:
        health = {item["source_name"]: item for item in self.repository.source_health()}
        return {"jobs": [{"job_id": item.id, "source_name": item.source_name, "source_health": health.get(item.source_name, {})} for item in self.repository.get_many(args["job_ids"])]}

    def _run_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        actions: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {"search_jobs": self._search_jobs, "get_job_details": self._get_job_details, "analyze_resume_for_jobs": self._analyze_resume, "get_source_freshness": self._source_freshness}
        try: return actions[name](args)
        except (KeyError, TypeError, ValueError) as error: return {"error": f"{name}: {error}"}

    @staticmethod
    def _instructions() -> str:
        return "You are CareerAgent. Use only supplied local tools for job facts, requirements, status and freshness. Do not claim a job is open unless status=open. Do not predict hiring outcomes or invent jobs, deadlines, requirements, or URLs. Before recommending a specific job, retrieve its details. Cite concrete job claims as [job_id]. Respond in concise Chinese with conclusion, 2-4 next actions, and one caveat."

    def _fallback(self, request: CopilotRequest, reason: str) -> dict[str, Any]:
        plan = self.fallback.plan(request)
        plan["agent"] = {"mode": "deterministic_fallback", "used_llm": False, "reason": reason}
        return plan

    def plan(self, request: CopilotRequest, *, use_llm: bool) -> dict[str, Any]:
        if not use_llm: return self._fallback(request, "external_llm_consent_not_given")
        if not self.settings.enabled or (self.settings.provider != "ollama" and not self.settings.api_key):
            return self._fallback(request, "llm_not_configured")
        self.evidence, trace, calls, output_text = {}, [], 0, ""
        user_input = {"goal": request.target_role, "location": request.target_location, "campus_cycle": request.campus_cycle, "employment_kind": request.employment_kind, "scope": request.scope, "message": request.message, "resume_text": request.resume_text}
        conversation: list[dict[str, Any]] = [{"role": "user", "content": [{"type": "input_text", "text": json.dumps(user_input, ensure_ascii=False)}]}]
        try:
            for round_index in range(self.max_rounds):
                response = self.transport.create({"model": self.settings.model, "instructions": self._instructions(), "input": conversation, "tools": TOOL_SPECS, "tool_choice": "required" if round_index == 0 else "auto", "max_output_tokens": self.settings.max_output_tokens, "store": False})
                output = list(response.get("output") or [])
                function_calls = [item for item in output if item.get("type") == "function_call"]
                output_text = str(response.get("output_text") or output_text)
                if not function_calls: break
                tool_outputs = []
                for call in function_calls:
                    calls += 1
                    if calls > self.max_calls: raise RuntimeError("tool_call_limit_reached")
                    try: args = json.loads(call.get("arguments") or "{}")
                    except json.JSONDecodeError: args = {}
                    result = self._run_tool(str(call.get("name")), args)
                    safe_args = {key: (f"<{len(value)} chars>" if key == "resume_text" and isinstance(value, str) else value) for key, value in args.items()}
                    trace.append({"tool": call.get("name"), "arguments": safe_args, "ok": "error" not in result})
                    tool_outputs.append({"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps(result, ensure_ascii=False)})
                conversation = output + tool_outputs
            else: raise RuntimeError("tool_round_limit_reached")
        except Exception as error:
            return self._fallback(request, f"llm_runtime_error:{type(error).__name__}")
        plan = self.fallback.plan(request)
        citations = list(self.evidence.values())[:6]
        plan.update({"mode": "llm_tool_calling", "summary": output_text or plan["summary"], "citations": citations or plan["citations"], "agent": {"mode": "responses_function_calling", "provider": self.settings.provider, "model": self.settings.model, "used_llm": True, "tool_calls": trace, "evidence_count": len(citations)}})
        return plan

    def to_dict(self, request: CopilotRequest, *, use_llm: bool) -> dict[str, Any]:
        return {"request": request.__dict__, "plan": self.plan(request, use_llm=use_llm)}
