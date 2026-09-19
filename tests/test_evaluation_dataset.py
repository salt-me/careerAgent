from __future__ import annotations

from career_agent.platform.evaluation_dataset import load_labeled_cases, score_retrieval_cases


def test_jsonl_template_loads_and_only_ready_cases_are_scored() -> None:
    cases = load_labeled_cases("evals/careeragent_eval_template.jsonl")
    assert len(cases) == 6
    assert score_retrieval_cases(cases, reference_to_job_id={}, search=lambda _: []).cases == 0
