"""A deliberately small, auditable skill catalogue for structured matching."""

from __future__ import annotations

import re


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "SQL": ("sql", "mysql", "postgresql", "sqlite"),
    "机器学习": ("机器学习", "machine learning", "ml"),
    "深度学习": ("深度学习", "deep learning", "dl"),
    "PyTorch": ("pytorch", "torch"),
    "Transformer": ("transformer", "attention"),
    "LLM": ("llm", "大语言模型", "大模型", "language model"),
    "RAG": ("rag", "检索增强", "retrieval augmented"),
    "LangGraph": ("langgraph",),
    "LangChain": ("langchain",),
    "FastAPI": ("fastapi",),
    "Docker": ("docker", "docker compose"),
    "Git": ("git", "github"),
    "Linux": ("linux",),
    "向量检索": ("向量检索", "embedding", "向量数据库", "vector search"),
    "重排序": ("rerank", "重排序", "re-ranking"),
    "评测": ("评测", "evaluation", "benchmark", "recall@"),
    "NLP": ("nlp", "自然语言处理"),
}


def extract_skills(text: str) -> set[str]:
    """Return canonical skills explicitly present in text.

    This is intentionally conservative: absence means only "missing evidence", never
    that a candidate lacks the skill.
    """
    normalized = text.lower()
    found: set[str] = set()
    for skill, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            if alias.isascii() and alias.isalnum() and len(alias) <= 3:
                if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", normalized):
                    found.add(skill)
                    break
            elif alias in normalized:
                found.add(skill)
                break
    return found


def sentences(text: str) -> list[str]:
    pieces = re.split(r"[\n。！？!?；;]+", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def evidence_for_skill(text: str, skill: str) -> str | None:
    aliases = SKILL_ALIASES[skill]
    for sentence in sentences(text):
        lowered = sentence.lower()
        if any(alias in lowered for alias in aliases):
            return sentence[:220]
    return None
