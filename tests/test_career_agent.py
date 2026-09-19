from __future__ import annotations

import unittest

from career_agent.critic import validate
from career_agent.documents import load_corpus
from career_agent.evaluation import evaluate_retrieval
from career_agent.matching import build_match_report
from career_agent.retrieval import LocalRetriever
from career_agent.workflow import CareerWorkflow


RESUME = "我使用 Python、RAG 和 Docker 完成知识库问答项目，并为检索链路写了评测脚本。"
JD = "岗位要求：熟悉 Python、RAG 和评测。加分项：熟悉 LangGraph。"


class CareerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.retriever = LocalRetriever(load_corpus())

    def test_retrieval_evaluation_has_reasonable_baseline(self) -> None:
        metrics = evaluate_retrieval(top_k=3)
        self.assertEqual(metrics["cases"], 12)
        self.assertGreaterEqual(metrics["recall_at_k"], 0.75)

    def test_missing_resume_evidence_is_not_a_negative_capability_claim(self) -> None:
        report = build_match_report(RESUME, JD, self.retriever)
        langgraph = next(item for item in report.dimensions if item.skill == "LangGraph")
        self.assertEqual(langgraph.status, "missing_evidence")
        self.assertIn("不等同于能力缺失", report.summary)

    def test_critic_requires_grounded_outputs(self) -> None:
        report = build_match_report(RESUME, JD, self.retriever)
        critic = validate(report, [])
        self.assertTrue(critic.passed)
        self.assertTrue(critic.checks["core_input_cited"])

    def test_workflow_returns_trace_and_questions(self) -> None:
        result = CareerWorkflow().run(RESUME, JD, route="interview")
        self.assertTrue(result.critic and result.critic.passed)
        self.assertGreaterEqual(len(result.interview_questions), 1)
        self.assertEqual(result.trace[-1]["node"], "workflow")


if __name__ == "__main__":
    unittest.main()
