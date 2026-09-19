"""Privacy-preserving local parsing for text and DOCX resumes."""

from __future__ import annotations

import re
import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO

from .career_intelligence import clean_text, extract_skills


class ResumeParseError(ValueError):
    pass


_SECTION_MARKERS = {
    "education": ("education", "教育", "学历", "学校"),
    "experience": ("experience", "工作经历", "实习经历", "工作经验"),
    "projects": ("project", "项目经历", "项目经验", "项目"),
    "skills": ("skills", "technical skills", "技能", "专业技能"),
}


@dataclass(frozen=True)
class ResumeProfile:
    normalized_text: str
    character_count: int
    detected_sections: list[str]
    skills: list[str]
    project_evidence_count: int
    experience_evidence_count: int
    parser: str

    def to_dict(self) -> dict:
        return asdict(self)


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", "replace")
    except (KeyError, OSError, zipfile.BadZipFile) as error:
        raise ResumeParseError("无法读取 DOCX 文件，请导出为标准 .docx 或粘贴文本。") from error
    paragraphs = re.sub(r"</w:p[^>]*>", "\n", xml)
    paragraphs = re.sub(r"<w:tab[^>]*/>", "\t", paragraphs)
    return re.sub(r"<[^>]+>", "", paragraphs)


def resume_text_from_bytes(data: bytes, filename: str, content_type: str = "") -> tuple[str, str]:
    if not data:
        raise ResumeParseError("简历文件为空。")
    if len(data) > 2_000_000:
        raise ResumeParseError("简历文件超过 2MB，请上传精简版或粘贴文本。")
    suffix = filename.rsplit(".", 1)[-1].casefold() if "." in filename else ""
    if suffix in {"txt", "md"} or content_type.startswith("text/"):
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return data.decode(encoding), "plain_text"
            except UnicodeDecodeError:
                continue
        raise ResumeParseError("文本编码无法识别，请保存为 UTF-8 后重试。")
    if suffix == "docx" or "wordprocessingml" in content_type:
        return _docx_text(data), "docx"
    if suffix == "pdf" or content_type == "application/pdf":
        raise ResumeParseError("当前版本支持 TXT 和 DOCX；PDF 请先导出为 DOCX/TXT 或粘贴文本。")
    raise ResumeParseError("仅支持 TXT、MD 和 DOCX 简历文件。")


def parse_resume_text(text: str, *, parser: str = "plain_text") -> ResumeProfile:
    normalized = clean_text(text)
    if len(normalized) < 10:
        raise ResumeParseError("简历内容过短，无法解析。")
    folded = normalized.casefold()
    sections = [name for name, markers in _SECTION_MARKERS.items() if any(marker in folded for marker in markers)]
    lines = [line for line in re.split(r"[\n。；;]+", text) if line.strip()]
    project_count = sum(bool(re.search(r"project|项目|系统|平台|作品", line, re.IGNORECASE)) for line in lines)
    experience_count = sum(bool(re.search(r"intern|实习|工作|company|公司", line, re.IGNORECASE)) for line in lines)
    return ResumeProfile(
        normalized_text=normalized,
        character_count=len(normalized),
        detected_sections=sections,
        skills=extract_skills(normalized),
        project_evidence_count=project_count,
        experience_evidence_count=experience_count,
        parser=parser,
    )


def parse_resume_bytes(data: bytes, filename: str, content_type: str = "") -> ResumeProfile:
    text, parser = resume_text_from_bytes(data, filename, content_type)
    return parse_resume_text(text, parser=parser)
