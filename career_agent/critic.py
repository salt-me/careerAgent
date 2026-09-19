"""Deterministic guardrails for evidence coverage and unsafe claims."""

from __future__ import annotations

from .models import CriticReport, InterviewQuestion, MatchReport


UNSUPPORTED_PHRASES = ("保证 offer", "必然拿到", "一定通过", "完全匹配")


def validate(match: MatchReport, questions: list[InterviewQuestion]) -> CriticReport:
    issues: list[str] = []
    allowed_ids = {citation.document_id for citation in match.citations}
    has_core_input = {"resume_input", "jd_input"}.issubset(allowed_ids)
    all_dimensions_grounded = all(
        bool(item.jd_evidence) and (item.status == "missing_evidence" or bool(item.resume_evidence))
        for item in match.dimensions
    )
    all_questions_grounded = all(
        question.citations and all(citation.document_id in allowed_ids for citation in question.citations)
        for question in questions
    )
    no_overclaim = not any(phrase in match.summary for phrase in UNSUPPORTED_PHRASES)
    if not has_core_input:
        issues.append("缺少简历或 JD 原始证据，不能输出匹配结论。")
    if not all_dimensions_grounded:
        issues.append("至少一个匹配维度缺少 JD 或简历证据。")
    if not all_questions_grounded:
        issues.append("至少一个面试问题没有可追溯引用。")
    if not no_overclaim:
        issues.append("回答包含无法验证的确定性求职承诺。")
    checks = {
        "core_input_cited": has_core_input,
        "dimensions_grounded": all_dimensions_grounded,
        "questions_grounded": all_questions_grounded,
        "no_overclaim": no_overclaim,
    }
    return CriticReport(passed=not issues, issues=issues, checks=checks)
