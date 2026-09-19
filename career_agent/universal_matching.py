"""Explainable matching that works across technical and non-technical roles."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable


SKILL_VOCABULARY: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "Java": ("java",),
    "Go": ("golang", "go语言"),
    "C++": ("c++", "cpp"),
    "SQL": ("sql",),
    "数据结构与算法": ("数据结构", "算法"),
    "Linux": ("linux",),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "CI/CD": ("ci/cd", "cicd", "持续集成"),
    "React": ("react",),
    "Vue": ("vue", "vue.js"),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript", "ts"),
    "HTML/CSS": ("html", "css"),
    "自动化测试": ("自动化测试", "selenium", "playwright"),
    "接口测试": ("接口测试", "api测试"),
    "测试用例": ("测试用例",),
    "性能测试": ("性能测试", "jmeter"),
    "监控告警": ("监控", "告警", "prometheus"),
    "故障应急": ("故障", "应急", "oncall", "on-call"),
    "数据建模": ("数据建模", "数仓", "数据仓库"),
    "ETL": ("etl", "数据清洗"),
    "Spark/Flink": ("spark", "flink"),
    "Hive/Kafka": ("hive", "kafka"),
    "Excel": ("excel",),
    "Tableau/Power BI": ("tableau", "power bi", "powerbi"),
    "指标体系": ("指标体系", "指标", "看板"),
    "需求分析": ("需求分析", "需求调研"),
    "用户研究": ("用户研究", "用户访谈", "用户洞察"),
    "PRD/原型": ("prd", "原型", "axure", "figma"),
    "A/B测试": ("a/b", "ab测试", "a/b测试"),
    "项目管理": ("项目管理", "里程碑", "风险管理"),
    "内容策划": ("内容策划", "选题", "文案"),
    "短视频制作": ("短视频", "视频剪辑", "拍摄"),
    "平台运营": ("小红书", "抖音", "视频号", "公众号"),
    "增长分析": ("增长", "留存", "转化", "漏斗"),
    "客户开发": ("客户开发", "拓客", "线索"),
    "商务谈判": ("商务谈判", "谈判", "签约"),
    "CRM": ("crm", "客户关系"),
    "招聘": ("招聘", "筛选", "面试"),
    "员工关系": ("员工关系", "入职", "离职", "劳动合同"),
    "薪酬社保": ("薪酬", "社保", "公积金", "考勤"),
    "会计核算": ("会计", "账务", "核算"),
    "税务": ("税务", "报税"),
    "财务报表": ("财务报表", "利润表", "资产负债表"),
    "UI/UX设计": ("ui", "ux", "交互设计", "视觉设计"),
    "用户体验": ("用户体验", "信息架构", "设计规范"),
    "供应链": ("供应链", "库存", "履约", "仓配"),
    "采购": ("采购", "供应商", "比价"),
    "法务合规": ("法务", "合规", "合同审阅"),
    "大模型": ("大模型", "llm", "rag", "agent"),
    "分布式系统": ("分布式", "高并发"),
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def extract_universal_skills(text: str) -> list[str]:
    normalised = _normalise(text)
    return [
        skill
        for skill, aliases in SKILL_VOCABULARY.items()
        if any(alias.casefold() in normalised for alias in aliases)
    ]


@dataclass(frozen=True)
class UniversalMatch:
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    resume_skills: list[str]
    job_skills: list[str]
    evidence: list[str]
    gap_actions: list[str]
    boundary_notice: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _ordered_difference(required: Iterable[str], existing: Iterable[str]) -> list[str]:
    existing_set = set(existing)
    return [skill for skill in required if skill not in existing_set]


def _gap_actions(job_family: str, missing: list[str]) -> list[str]:
    actions = [f"选取一个 {job_family} 场景，补齐可验证的项目或案例，而不是只罗列技能。"]
    if missing:
        actions.append(f"优先补齐：{'、'.join(missing[:3])}，并在简历中写明任务、方法、结果。")
    actions.append("用目标岗位的语言改写一段项目经历，并准备一次 2 分钟的结果复盘。")
    return actions


def build_universal_match(resume_text: str, record: dict) -> UniversalMatch:
    """Calculate transparent skill coverage; this never claims hiring probability."""
    resume_skills = extract_universal_skills(resume_text)
    job_skills = extract_universal_skills(record["text"])
    matched = [skill for skill in job_skills if skill in set(resume_skills)]
    missing = _ordered_difference(job_skills, resume_skills)

    if job_skills:
        coverage = len(matched) / len(job_skills)
        score = min(95, round(20 + coverage * 75))
    else:
        score = 20
    if record["job_family"].lower() in resume_text.lower():
        score = min(95, score + 5)

    evidence = [
        f"目标记录识别到 {len(job_skills)} 项可解释能力标签；简历命中 {len(matched)} 项。",
        f"命中能力：{'、'.join(matched) if matched else '未识别到词表内直接命中，请补充项目和技能描述。'}",
    ]
    boundary = None
    if not record["live_vacancy"]:
        boundary = "这是市场岗位画像，不是可直接投递的招聘职位；结果仅用于职业方向和简历准备。"
    return UniversalMatch(
        match_score=score,
        matched_skills=matched,
        missing_skills=missing,
        resume_skills=resume_skills,
        job_skills=job_skills,
        evidence=evidence,
        gap_actions=_gap_actions(record["job_family"], missing),
        boundary_notice=boundary,
    )
