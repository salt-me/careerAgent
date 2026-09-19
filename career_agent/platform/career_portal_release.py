"""Latest portal shell: adds local resume-file parsing to the production UI."""

from __future__ import annotations

from .career_portal_production import CAREER_PORTAL_PRODUCTION_HTML


_FILE_PICKER = """<div class=\"row\" style=\"margin:0 0 8px\"><input id=\"resumeFile\" type=\"file\" accept=\".txt,.md,.docx\" class=\"grow\"><span id=\"resumeFileStatus\" class=\"quality\">支持 TXT / DOCX，本地请求后不保存文件。</span></div>"""
_PARSER_SCRIPT = """
async function parseResumeFile(){const file=el('resumeFile').files[0];if(!file)return;const status=el('resumeFileStatus');status.textContent='正在本地解析文件…';try{const r=await fetch('/api/career/resume/parse?filename='+encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream'},body:file});const d=await r.json();if(!r.ok)throw Error(d.detail||'解析失败');el('resume').value=d.normalized_text;status.textContent=`已读取 ${d.parser} 简历：${d.character_count} 字，识别 ${d.skills.length} 项技能。`}catch(e){status.textContent='解析失败：'+e.message}}
"""

CAREER_PORTAL_RELEASE_HTML = CAREER_PORTAL_PRODUCTION_HTML.replace(
    '<textarea id="resume"', _FILE_PICKER + '<textarea id="resume"'
).replace(
    "el('searchForm').onsubmit=e=>{e.preventDefault();search()};",
    _PARSER_SCRIPT + "el('resumeFile').onchange=parseResumeFile;el('searchForm').onsubmit=e=>{e.preventDefault();search()};",
)
