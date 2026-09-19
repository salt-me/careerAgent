"""Deterministic job-type and campus-cycle classification."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class JobTaxonomy:
    employment_kind: str
    campus_cycle: str
    job_group: str
    confidence: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _contains_marker(text: str, marker: str) -> bool:
    """Use token boundaries for Latin role labels; CJK phrases remain contiguous."""
    if re.fullmatch(r"[a-z0-9 .+/#-]+", marker):
        return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text) is not None
    return marker in text

def _cycle(text: str) -> str:
    for year in ("2029", "2028", "2027", "2026", "2025", "2024"):
        if year not in text and f"{year[-2:]}届" not in text:
            continue
        if any(marker in text for marker in ("秋招", "秋季", "fall", "autumn")):
            return f"{year}_autumn"
        if any(marker in text for marker in ("春招", "春季", "spring")):
            return f"{year}_spring"
        return f"{year}_campus_unspecified"
    if any(marker in text for marker in ("校招", "校园招聘", "应届", "毕业生", "graduate program", "new grad", "campus")):
        return "campus_unspecified"
    return "not_applicable"


def _employment_kind(text: str, cycle: str) -> str:
    if any(marker in text for marker in ("实习", "internship", "intern")):
        return "internship"
    if cycle != "not_applicable":
        return "campus"
    if any(marker in text for marker in ("社招", "社会招聘", "experienced", "senior", "full-time")) or re.search(r"\b[1-9]\d?\s*years?\b|[1-9]\d?\s*年(?:以上)?(?:经验|工作)", text):
        return "experienced"
    return "unknown"


def _job_group(title: str, description: str = "", declared_group: str = "") -> str:
    """Classify the occupation from the role title before using JD context.

    A JD may mention product, growth or data many times while the actual role is
    an engineer, designer or marketer.  Therefore broad description keywords
    are only a last resort, and the product family requires management intent.
    """
    title_text = _normalise(title)
    declared_text = _normalise(declared_group)
    context_text = _normalise(f"{declared_group} {description}")

    product_management_markers = (
        "\u4ea7\u54c1\u7ecf\u7406", "\u4ea7\u54c1\u7b56\u5212", "\u4ea7\u54c1\u6218\u7565", "\u4ea7\u54c1\u7ba1\u7406", "\u4ea7\u54c1\u52a9\u7406", "\u4ea7\u54c1\u5b9e\u4e60",
        "product manager", "product owner", "product management", "product strategy", "product analyst", "product specialist", "product intern",
    )
    if any(_contains_marker(title_text, marker) for marker in product_management_markers):
        return "product"

    # Title-level occupational indicators take precedence over incidental words
    # such as "product", "growth" or "data" elsewhere in a JD.
    title_groups = (
        ("engineering", ("\u540e\u7aef", "\u524d\u7aef", "\u5f00\u53d1", "\u5de5\u7a0b\u5e08", "\u6280\u672f", "software engineer", "engineer", "developer", "sre", "devops", "architect", "backend", "front-end", "frontend", "platform")),
        ("data", ("\u6570\u636e\u79d1\u5b66", "\u6570\u636e\u5206\u6790", "\u7b97\u6cd5", "\u673a\u5668\u5b66\u4e60", "data scientist", "data analyst", "machine learning", "research scientist", "analytics")),
        ("design", ("\u8bbe\u8ba1", "designer", "ux", "ui", "user experience")),
        ("marketing", ("\u5e02\u573a", "\u8425\u9500", "marketing", "growth", "content strategist", "brand")),
        ("operations", ("\u8fd0\u8425", "\u9879\u76ee\u7ba1\u7406", "operations", "supply chain", "program manager", "project manager")),
        ("sales", ("\u9500\u552e", "\u5546\u52a1", "sales", "business development", "account executive")),
        ("hr", ("\u4eba\u529b", "\u62db\u8058", "recruiter", "recruiting", "talent acquisition", "human resources")),
        ("finance", ("\u8d22\u52a1", "\u4f1a\u8ba1", "finance", "accounting", "controller")),
        ("legal", ("\u6cd5\u52a1", "\u5408\u89c4", "legal", "compliance", "counsel", "attorney")),
        ("healthcare", ("\u533b\u7597", "\u62a4\u7406", "health", "clinical", "nurse")),
        ("education", ("\u6559\u80b2", "\u6559\u5e08", "education", "teacher")),
    )
    for group, markers in title_groups:
        if any(_contains_marker(title_text, marker) for marker in markers):
            return group

    # Department labels are a stronger fallback than prose.  Product remains
    # intentionally strict: a generic product mention in a JD is insufficient.
    for group, markers in title_groups:
        if any(_contains_marker(declared_text, marker) for marker in markers):
            return group
    if any(_contains_marker(declared_text, marker) for marker in product_management_markers):
        return "product"

    context_groups = tuple((group, markers) for group, markers in title_groups if group != "product")
    for group, markers in context_groups:
        if any(_contains_marker(context_text, marker) for marker in markers):
            return group
    if any(_contains_marker(context_text, marker) for marker in product_management_markers):
        return "product"
    return "other"

def classify_job(title: str, description: str = "", declared_group: str = "") -> JobTaxonomy:
    text = _normalise(f"{title} {description} {declared_group}")
    cycle = _cycle(text)
    employment_kind = _employment_kind(text, cycle)
    group = _job_group(title, description, declared_group)
    confidence = "high" if cycle != "not_applicable" or employment_kind != "unknown" else "low"
    return JobTaxonomy(employment_kind=employment_kind, campus_cycle=cycle, job_group=group, confidence=confidence)


def cycle_guidance(campus_cycle: str, employment_kind: str) -> list[str]:
    if employment_kind == "internship":
        return ["明确可实习的起止时间与每周到岗天数。", "突出一个可运行项目及个人负责部分。"]
    if campus_cycle.endswith("_autumn"):
        return ["按秋招节奏准备网申、笔试和两轮项目讲解。", "用目标届别的语言改写教育经历与毕业时间。"]
    if campus_cycle.endswith("_spring"):
        return ["优先投递补录、提前批与仍开放的春招岗位。", "准备更紧凑的项目复盘与可立即到岗说明。"]
    if employment_kind == "experienced":
        return ["突出可量化业务结果、职责范围和主导程度。", "按目标岗位重排最近两段工作经历。"]
    return ["确认目标岗位所属届别和招聘状态。", "用岗位关键词补齐简历中的项目证据。"]