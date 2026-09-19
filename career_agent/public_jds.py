"""Curated public JD metadata with source/date provenance.

Only short, human-written summaries are kept locally. The source URL remains the
authoritative location for the original listing and should be refreshed before use.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PUBLIC_JD_PATH = Path(__file__).resolve().parent / "data" / "public_jds.json"


def load_public_jds(path: str | Path | None = None) -> list[dict[str, Any]]:
    return json.loads(Path(path or PUBLIC_JD_PATH).read_text(encoding="utf-8"))


def find_public_jd(job_id: str) -> dict[str, Any]:
    for job in load_public_jds():
        if job["id"] == job_id:
            return job
    raise KeyError(f"未找到公开 JD：{job_id}")
