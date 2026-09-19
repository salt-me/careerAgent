from __future__ import annotations

from career_agent.platform.evaluation import RetrievalCase, evaluate_retrieval


def test_retrieval_evaluation_reports_hit_rates_and_mrr() -> None:
    rankings = {"python": ["job-1", "job-2"], "product": ["job-9", "job-3", "job-2"]}
    result = evaluate_retrieval(
        [RetrievalCase("python", ("job-1",)), RetrievalCase("product", ("job-3",))],
        lambda query: rankings[query],
    )
    assert result.hit_at_1 == 0.5
    assert result.hit_at_3 == 1.0
    assert result.mean_reciprocal_rank == 0.75
