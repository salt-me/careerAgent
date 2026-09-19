"""Production-only portal additions kept separate from earlier compatibility UI."""

from __future__ import annotations

from .career_portal_next import CAREER_PORTAL_NEXT_HTML


_CATEGORY = """<select id=\"jobGroup\"><option value=\"\">全部类别</option><option value=\"engineering\">研发/测试</option><option value=\"data\">数据/算法</option><option value=\"product\">产品</option><option value=\"design\">设计</option><option value=\"operations\">运营/项目</option><option value=\"sales\">销售/商务</option><option value=\"marketing\">市场/增长</option><option value=\"finance\">财务</option><option value=\"hr\">人力资源</option><option value=\"legal\">法务/合规</option></select>"""

CAREER_PORTAL_PRODUCTION_HTML = CAREER_PORTAL_NEXT_HTML.replace(
    '<input id="location" placeholder="地点">', _CATEGORY + '<input id="location" placeholder="地点">'
).replace(
    "employment_kind:el('kind').value,location:el('location').value.trim()",
    "employment_kind:el('kind').value,job_group:el('jobGroup').value,location:el('location').value.trim()",
)
