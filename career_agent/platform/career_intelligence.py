"""Search, matching and text-cleaning primitives for the job-seeker portal.

The functions in this module are deliberately deterministic.  They provide a
transparent retrieval/matching layer above the vector recall service and never
present a score as a prediction of an employer's hiring decision.
"""

from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


SKILL_CATALOG: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "Java": ("java",),
    "Go": ("golang", "go language", "go语言"),
    "C++": ("c++", "cpp"),
    "SQL": ("sql", "mysql", "postgresql", "postgres"),
    "Data structures & algorithms": ("data structure", "algorithm", "数据结构", "算法"),
    "Linux": ("linux",),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "CI/CD": ("ci/cd", "cicd", "continuous integration"),
    "React": ("react",),
    "Vue": ("vue", "vue.js"),
    "TypeScript": ("typescript",),
    "JavaScript": ("javascript",),
    "Testing": ("testing", "pytest", "playwright", "selenium", "自动化测试", "测试开发"),
    "Machine learning": ("machine learning", "机器学习", "深度学习", "deep learning"),
    "LLM/RAG": ("llm", "rag", "大模型", "agent", "智能体"),
    "Data analysis": ("data analysis", "数据分析", "pandas", "excel", "tableau", "power bi"),
    "Spark/Flink": ("spark", "flink"),
    "Product discovery": ("product requirement", "prd", "需求分析", "用户研究", "用户访谈"),
    "Figma": ("figma", "axure", "prototype", "原型"),
    "Growth experimentation": ("a/b test", "ab test", "增长", "转化", "留存"),
    "Project management": ("project management", "项目管理", "scrum", "agile"),
    "Sales": ("sales", "business development", "客户开发", "商务谈判"),
    "Marketing": ("marketing", "content strategy", "市场", "营销", "内容运营"),
    "Accounting": ("accounting", "会计", "财务报表", "税务"),
    "Recruiting": ("recruiting", "talent acquisition", "招聘", "人才招聘"),
    "Legal & compliance": ("legal", "compliance", "法务", "合规", "合同审阅"),
    "Supply chain": ("supply chain", "采购", "库存", "物流", "供应链"),
}

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9+#./-]+|[\u4e00-\u9fff]{2,}", re.IGNORECASE)


def clean_text(value: str | None, *, limit: int | None = None) -> str:
    """Convert a description copied from an ATS into display-safe plain text."""
    text = html.unescape(value or "")
    text = _TAG.sub(" ", text)
    text = _SPACE.sub(" ", text).strip()
    return text[:limit].rstrip() if limit else text


def extract_skills(text: str) -> list[str]:
    folded = clean_text(text).casefold()
    return [name for name, aliases in SKILL_CATALOG.items() if any(alias.casefold() in folded for alias in aliases)]


def _tokens(value: str) -> list[str]:
    return _TOKEN.findall(clean_text(value).casefold())


def _normalised_key(value: str) -> str:
    return "".join(_tokens(value))


def canonical_job_key(record: dict[str, Any]) -> str:
    return f"{_normalised_key(str(record.get('company', '')))}::{_normalised_key(str(record.get('title', '')))}"


def _freshness(record: dict[str, Any]) -> float:
    raw = record.get("last_verified_at") or record.get("last_seen_at")
    if not raw:
        return 0.35
    try:
        seen = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        age = max(0.0, (datetime.now(timezone.utc) - seen).total_seconds() / 86400)
    except ValueError:
        return 0.35
    return max(0.1, min(1.0, 1 - age / 30))


def _lexical_score(query: str, record: dict[str, Any]) -> tuple[float, list[str]]:
    query_tokens = list(dict.fromkeys(_tokens(query)))
    if not query_tokens:
        return 0.0, []
    title = clean_text(str(record.get("title", ""))).casefold()
    haystack = " ".join(
        clean_text(str(record.get(key, ""))).casefold()
        for key in ("title", "company", "location", "job_group", "text")
    )
    matched = [token for token in query_tokens if token in haystack]
    if not matched:
        return 0.0, []
    score = len(matched) / len(query_tokens)
    score += 0.25 * sum(token in title for token in matched) / len(query_tokens)
    return min(1.0, score), matched


def hybrid_rerank(
    query: str,
    records: Iterable[dict[str, Any]],
    semantic_scores: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Combine vector recall, lexical intent and verification recency.

    Callers provide records selected by vector recall.  A lexical component then
    keeps exact role/company terms prominent while freshness prevents stale
    records from outranking equally relevant, verified live jobs.
    """
    semantic_scores = semantic_scores or {}
    deduplicated: dict[str, dict[str, Any]] = {}
    duplicate_counts: Counter[str] = Counter(canonical_job_key(record) for record in records)
    for record in records:
        item = dict(record)
        semantic = max(0.0, min(1.0, float(semantic_scores.get(str(item.get("id")), 0.0))))
        lexical, matched_terms = _lexical_score(query, item)
        freshness = _freshness(item)
        final = round((0.62 * semantic + 0.28 * lexical + 0.10 * freshness) * 100, 1)
        item["excerpt"] = clean_text(str(item.get("excerpt") or item.get("text", "")), limit=260)
        item["ranking"] = {
            "score": final,
            "semantic": round(semantic, 3),
            "lexical": round(lexical, 3),
            "freshness": round(freshness, 3),
            "matched_terms": matched_terms,
            "explanation": "语义召回 + 关键词匹配 + 最近核验时间",
        }
        key = canonical_job_key(item)
        item["duplicate_count"] = duplicate_counts[key]
        current = deduplicated.get(key)
        if current is None or item["ranking"]["score"] > current["ranking"]["score"]:
            deduplicated[key] = item
    return sorted(deduplicated.values(), key=lambda item: item["ranking"]["score"], reverse=True)


@dataclass(frozen=True)
class MatchInsight:
    score: int
    readiness: str
    matched_skills: list[str]
    missing_skills: list[str]
    resume_skills: list[str]
    job_skills: list[str]
    evidence: list[str]
    preparation_actions: list[str]
    boundary_notice: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_match_insight(resume_text: str, record: dict[str, Any]) -> MatchInsight:
    """Return a transparent preparation signal, not a hiring-probability score."""
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(str(record.get("text", "")))
    matched = [skill for skill in job_skills if skill in set(resume_skills)]
    missing = [skill for skill in job_skills if skill not in set(resume_skills)]
    coverage = len(matched) / len(job_skills) if job_skills else 0
    score = min(95, round(25 + 70 * coverage)) if job_skills else 25
    readiness = "准备充分" if coverage >= 0.7 else "有针对性补齐空间" if coverage >= 0.35 else "建议先补足核心证据"
    title = str(record.get("title", "目标岗位"))
    evidence = [
        f"该岗位文本识别到 {len(job_skills)} 项可解释能力标签，简历直接覆盖 {len(matched)} 项。",
        f"已覆盖：{'、'.join(matched) if matched else '暂未识别到技能词表内的直接命中'}。",
        f"优先补齐：{'、'.join(missing[:4]) if missing else '可将已有能力改写为岗位语言并补充量化结果'}。",
    ]
    actions = [
        f"为“{title}”挑选一段最相关的项目经历，写清任务、方法、结果和个人贡献。",
        *( [f"先补一项可验证产出：围绕 {missing[0]} 做小项目、案例复盘或作品页。"] if missing else [] ),
        "用岗位中的关键词改写简历标题、项目小标题和技能栏；不要声称没有做过的经历。",
        "准备 2 分钟项目复盘，并在投递前到官方链接确认岗位仍开放。",
    ]
    status = str(record.get("lifecycle_status", "unverified"))
    boundary = (
        "这是准备度提示，不是录用概率（not a hiring probability）；岗位当前为开放记录，仍请以官方页面为准。"
        if status == "open"
        else "这是历史或未核验记录，仅用于方向参考，不应视为可直接投递的岗位。"
    )
    return MatchInsight(score, readiness, matched, missing, resume_skills, job_skills, evidence, actions, boundary)
