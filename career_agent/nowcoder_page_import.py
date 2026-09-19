"""Import bounded, source-linked historical JD summaries from a public Nowcoder career page.

The importer deliberately does not bypass authentication or scrape private APIs.
It fetches one user-visible public careers page, preserves the page's individual
``data-id`` job identifier in the source URL, and writes a short controlled
summary rather than reproducing the full page text.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, asdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


DEFAULT_PAGE_URL = "https://www.nowcoder.com/careers/nowcoder1/413"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "licensed_sources" / "nowcoder_careers_413_public.jsonl"

_SKILL_TERMS = (
    "Java",
    "C++",
    "Python",
    "Go",
    "JavaScript",
    "TypeScript",
    "React",
    "Vue",
    "HTML5",
    "CSS3",
    "Linux",
    "SQL",
    "Spring",
    "TensorFlow",
    "机器学习",
    "深度学习",
    "数据分析",
    "分布式系统",
    "网络",
    "测试",
    "运维",
    "音视频",
    "产品",
    "运营",
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class _CareerPageParser(HTMLParser):
    """Parse only the public job cards, avoiding page chrome and account data."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.jobs: list[dict[str, str]] = []
        self.current: dict[str, Any] | None = None
        self.job_div_depth = 0
        self.capture: str | None = None
        self.capture_div_depth: int | None = None
        self.content_block_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "")
        if tag == "div" and self.current is None and "rec-job" in classes.split():
            job_id = _clean(attributes.get("data-id") or "")
            if not job_id:
                return
            self.current = {
                "source_job_id": job_id,
                "title_parts": [],
                "duty_parts": [],
                "requirement_parts": [],
                "city": "not_disclosed",
                "direction": "not_disclosed",
                "company": "not_disclosed",
            }
            self.job_div_depth = 1
            self.capture = None
            self.content_block_count = 0
            return

        if self.current is None:
            return
        if tag == "div":
            self.job_div_depth += 1
            if "js-duty-content" in classes.split():
                self.capture = "duty" if self.content_block_count == 0 else "requirement"
                self.capture_div_depth = self.job_div_depth
                self.content_block_count += 1
        elif tag == "h2":
            self.capture = "title"
        elif tag == "span":
            tooltip = _clean(attributes.get("title") or "")
            for label, key in (("工作城市：", "city"), ("职位方向：", "direction"), ("招聘公司：", "company")):
                if tooltip.startswith(label):
                    self.current[key] = _clean(tooltip.removeprefix(label)) or "not_disclosed"

    def handle_data(self, data: str) -> None:
        if self.current is None or self.capture is None:
            return
        text = _clean(data)
        if not text:
            return
        if self.capture == "title":
            self.current["title_parts"].append(text)
        elif self.capture == "duty":
            self.current["duty_parts"].append(text)
        elif self.capture == "requirement":
            self.current["requirement_parts"].append(text)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag == "h2" and self.capture == "title":
            self.capture = None
        if tag != "div":
            return
        if self.capture_div_depth == self.job_div_depth:
            self.capture = None
            self.capture_div_depth = None
        self.job_div_depth -= 1
        if self.job_div_depth != 0:
            return
        title = _clean(" ".join(self.current["title_parts"]))
        company = self.current["company"]
        if title and company != "not_disclosed":
            self.jobs.append(
                {
                    "source_job_id": self.current["source_job_id"],
                    "title": title,
                    "company": company,
                    "city": self.current["city"],
                    "direction": self.current["direction"],
                    "duty": _clean(" ".join(self.current["duty_parts"])),
                    "requirement": _clean(" ".join(self.current["requirement_parts"])),
                }
            )
        self.current = None
        self.capture = None
        self.capture_div_depth = None
        self.content_block_count = 0


def parse_public_career_page(html: str) -> list[dict[str, str]]:
    parser = _CareerPageParser()
    parser.feed(html)
    parser.close()
    return parser.jobs


def _keywords(*segments: str) -> list[str]:
    source = " ".join(segments).casefold()
    return [term for term in _SKILL_TERMS if term.casefold() in source][:8]


def _normalise_title(title: str, company: str) -> str:
    title = re.sub(r"^[【\[][^】\]]+[】\]]", "", title).strip()
    return title or company


def _raw_record(job: dict[str, str], *, page_url: str, captured_at: str) -> dict[str, str]:
    keywords = _keywords(job["title"], job["duty"], job["requirement"])
    keyword_text = "、".join(keywords) if keywords else "详见原始公开页面"
    source_url = f"{page_url}?{urlencode({'jobIds': job['source_job_id']})}"
    title = _normalise_title(job["title"], job["company"])
    return {
        "source_name": "nowcoder",
        "source_provider": "nowcoder",
        "source_license": "public-page-summary",
        "source_url": source_url,
        "source_page": page_url,
        "source_job_id": f"nowcoder-careers-413-{job['source_job_id']}",
        "source_status": "closed",
        "title": title,
        "company": job["company"],
        "position": job["direction"],
        "job_family": job["direction"],
        "location": job["city"],
        "experience": "not_disclosed",
        "employment_type": "not_disclosed",
        "published_at": "not_disclosed",
        "captured_at": captured_at,
        "text": (
            f"牛客公开职位摘要：{job['company']}的{title}，工作城市为{job['city']}，"
            f"页面职位方向为{job['direction']}。职责与任职要求的受控关键词包括：{keyword_text}。"
            "该公开招聘专场标示职位已结束，作为历史 JD 样本保留；申请前请以原页面为准。"
        ),
        "source_note": "Public historical Nowcoder career-page record; individual job ID is retained in source_job_id and source_url.",
    }


@dataclass(frozen=True)
class ImportSummary:
    source_page: str
    parsed_job_cards: int
    records_written: int
    output_path: str


def import_public_career_page(
    *,
    page_url: str = DEFAULT_PAGE_URL,
    output_path: Path = DEFAULT_OUTPUT,
    captured_at: str | None = None,
    max_records: int | None = None,
    overwrite: bool = False,
) -> ImportSummary:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing source batch: {output_path}")
    request = urllib.request.Request(page_url, headers={"User-Agent": "CareerAgent/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", errors="replace")
    jobs = parse_public_career_page(html)
    if not jobs:
        raise RuntimeError("No public Nowcoder job cards were found; page markup may have changed.")
    captured_at = captured_at or date.today().isoformat()
    selected = jobs[:max_records] if max_records else jobs
    records = [_raw_record(job, page_url=page_url, captured_at=captured_at) for job in selected]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8"
    )
    return ImportSummary(
        source_page=page_url,
        parsed_job_cards=len(jobs),
        records_written=len(records),
        output_path=str(output_path),
    )


def summary_as_dict(summary: ImportSummary) -> dict[str, Any]:
    return asdict(summary)

