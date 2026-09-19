from __future__ import annotations

import zipfile
from io import BytesIO

import pytest

from career_agent.platform.resume_parser import ResumeParseError, parse_resume_bytes


def test_resume_parser_reads_plain_text_and_extracts_profile() -> None:
    profile = parse_resume_bytes("教育背景\n项目经历：Python SQL Docker 平台".encode(), "resume.txt", "text/plain")
    assert profile.parser == "plain_text"
    assert "Python" in profile.skills
    assert "projects" in profile.detected_sections


def test_resume_parser_reads_standard_docx_without_extra_dependency() -> None:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>项目经历 Python SQL</w:t></w:r></w:p></w:body></w:document>")
    profile = parse_resume_bytes(output.getvalue(), "resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert profile.parser == "docx"
    assert "SQL" in profile.skills


def test_resume_parser_rejects_pdf_with_actionable_message() -> None:
    with pytest.raises(ResumeParseError, match="TXT 和 DOCX"):
        parse_resume_bytes(b"%PDF", "resume.pdf", "application/pdf")
