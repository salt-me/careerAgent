"""Evidence-first JD/resume matching. No claim is inferred from absent resume text."""

from __future__ import annotations

from .catalog import evidence_for_skill, extract_skills
from .documents import input_document
from .models import Citation, MatchDimension, MatchReport
from .retrieval import LocalRetriever, citation_from_hit


REQUIRED_MARKERS = ("要求", "必须", "熟悉", "掌握", "具备", "required", "must")


def _is_required(jd_text: str, skill: str) -> bool:
    evidence = evidence_for_skill(jd_text, skill) or ""
    return any(marker in evidence.lower() for marker in REQUIRED_MARKERS)


def _recommendation(skill: str, status: str) -> str:
    if status == "match":
        return f"在面试中用具体项目说明 {skill} 的使用场景、取舍和结果。"
    if status == "partial":
        return f"补充一段能证明 {skill} 深度的项目证据，并准备相关追问。"
    return f"简历中未检索到 {skill} 的直接证据；如确有经历，请补充真实项目描述，否则列为短期学习重点。"


def build_match_report(resume_text: str, jd_text: str, retriever: LocalRetriever) -> MatchReport:
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)
    dimensions: list[MatchDimension] = []
    for skill in sorted(jd_skills):
        resume_evidence = evidence_for_skill(resume_text, skill)
        jd_evidence = evidence_for_skill(jd_text, skill) or f"JD 中出现 {skill}"
        required = _is_required(jd_text, skill)
        if skill in resume_skills and resume_evidence:
            status = "match"
        elif skill in resume_skills:
            status = "partial"
        else:
            status = "missing_evidence"
        dimensions.append(
            MatchDimension(
                skill=skill,
                required=required,
                status=status,
                resume_evidence=resume_evidence,
                jd_evidence=jd_evidence,
                recommendation=_recommendation(skill, status),
            )
        )

    required_dimensions = [dimension for dimension in dimensions if dimension.required]
    weighted = required_dimensions or dimensions
    if not weighted:
        score = 0.0
    else:
        points = {"match": 1.0, "partial": 0.55, "missing_evidence": 0.0}
        score = round(100 * sum(points[item.status] for item in weighted) / len(weighted), 1)
    level = "strong" if score >= 75 else "potential" if score >= 45 else "needs_preparation"

    resume_document = input_document("resume_input", "用户提供的简历", resume_text)
    jd_document = input_document("jd_input", "用户提供的岗位 JD", jd_text)
    citations: list[Citation] = []
    for document in (resume_document, jd_document):
        excerpt = document.text[:280].strip()
        citations.append(Citation(document.id, document.title, document.source, excerpt))
    for hit in retriever.search(f"{jd_text}\n{resume_text}", top_k=3):
        citations.append(citation_from_hit(hit, jd_text))

    matched = sum(item.status == "match" for item in dimensions)
    gaps = [item.skill for item in dimensions if item.status == "missing_evidence"]
    summary = (
        f"在 {len(dimensions)} 个 JD 技能维度中检索到 {matched} 项直接简历证据；"
        f"当前匹配度为 {score}/100（{level}）。"
    )
    if gaps:
        summary += f" {', '.join(gaps[:4])} 属于简历中缺少直接证据的维度，不等同于能力缺失。"
    return MatchReport(score=score, level=level, dimensions=dimensions, citations=citations, summary=summary)
