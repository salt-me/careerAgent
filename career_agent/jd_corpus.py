"""Versioned, auditable public JD corpus used by the expanded vector index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CURATED_JD_PATH = Path(__file__).resolve().parent / "data" / "public_jds_expanded.json"


def load_curated_jds() -> list[dict[str, Any]]:
    return json.loads(CURATED_JD_PATH.read_text(encoding="utf-8"))


def find_curated_jd(job_id: str) -> dict[str, Any]:
    for job in load_curated_jds():
        if job["id"] == job_id:
            return job
    raise KeyError(f"未找到公开 JD：{job_id}")
