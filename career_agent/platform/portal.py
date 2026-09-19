"""Candidate-facing page layered over the lifecycle platform API."""

from __future__ import annotations

from fastapi.responses import HTMLResponse

from .service import PlatformComponents, create_platform_app


PORTAL_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CareerAgent｜岗位发现与准备助手</title>
<style>
:root{--ink:#172033;--muted:#63708a;--line:#e6eaf0;--blue:#315efb;--bg:#f7f8fb;--card:#fff;--green:#138a5b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Inter,"Microsoft YaHei",sans-serif}
main{max-width:1120px;margin:auto;padding:52px 24px 72px}.tag{color:var(--blue);font-weight:700;letter-spacing:.08em;font-size:12px}.hero{display:grid;grid-template-columns:1.3fr .7fr;gap:32px;align-items:end;margin-bottom:28px}h1{font-size:44px;line-height:1.12;margin:10px 0 14px;letter-spacing:-.04em}h2{font-size:20px;margin:0 0 12px}.sub{color:var(--muted);font-size:17px;max-width:720px}.stat{background:#18223b;color:#fff;border-radius:16px;padding:22px}.stat b{font-size:30px;display:block}.panel,.job{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:0 8px 28px #17203308}.search{display:grid;grid-template-columns:1fr 160px auto;gap:10px}input,select,textarea,button{font:inherit;border-radius:10px;border:1px solid #cfd6e3;padding:11px 13px}input,select,textarea{width:100%;background:#fff;color:var(--ink)}button{border:0;background:var(--blue);color:#fff;font-weight:700;cursor:pointer}button:hover{filter:brightness(.94)}.hint{color:var(--muted);font-size:13px;margin:10px 0 0}.layout{display:grid;grid-template-columns:1.25fr .75fr;gap:22px;margin-top:22px}.results{display:grid;gap:12px}.job h3{margin:0 0 5px;font-size:18px}.meta{color:var(--muted);font-size:13px}.badge{display:inline-block;border-radius:999px;padding:2px 9px;font-size:12px;font-weight:700;background:#e9fbf3;color:var(--green);margin-left:6px}.job p{color:#44506a;margin:11px 0}.job button{font-size:13px;padding:8px 12px}.sticky{position:sticky;top:20px;height:max-content}.result{display:none;margin-top:12px;padding:12px;border-radius:10px;background:#eff4ff;color:#24355d;white-space:pre-wrap}.empty{color:var(--muted);padding:34px;text-align:center}.foot{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:760px){main{padding:30px 16px}.hero,.layout{grid-template-columns:1fr}.search{grid-template-columns:1fr}h1{font-size:34px}.sticky{position:static}}
</style></head><body><main>
<div class="hero"><div><div class="tag">CAREERAGENT / LIVE JOB DISCOVERY</div><h1>找到还在招聘的岗位，知道下一步该准备什么。</h1><p class="sub">优先搜索官方招聘系统的实时岗位；历史记录仅作趋势参考。选择岗位后，粘贴简历即可获得匹配度、技能缺口和届别准备建议。</p></div><div class="stat"><span>实时数据状态</span><b id="total">—</b><span id="status">正在连接岗位库</span></div></div>
<section class="panel"><h2>搜索岗位</h2><form class="search" id="searchForm"><input id="query" required minlength="2" value="软件工程师" placeholder="例如：算法工程师、产品经理、金融分析"><select id="scope"><option value="live">只看在招</option><option value="all">在招 + 历史参考</option><option value="history">只看历史参考</option></select><button>搜索</button></form><div class="hint">“在招”仅代表最近一次成功同步仍由官方来源公开展示；投递前仍请以职位原链接为准。</div></section>
<div class="layout"><section><h2>岗位结果</h2><div id="results" class="results"><div class="empty">输入关键词开始搜索。</div></div></section><aside class="panel sticky"><h2>匹配我的简历</h2><p class="hint">先在左侧选择一条岗位，再粘贴简历文本。</p><textarea id="resume" rows="12" placeholder="例如：2027届软件工程专业；熟悉 Python、SQL、Docker；完成过 RAG 检索系统项目……"></textarea><button id="match" style="width:100%;margin-top:10px">生成匹配建议</button><div class="result" id="matchResult"></div></aside></div>
<p class="foot">CareerAgent 仅聚合允许访问的官方公开职位板或授权数据源，不替代招聘方官方网站。</p>
</main><script>
let selected=null; const el=id=>document.getElementById(id); const esc=s=>String(s||'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function health(){try{const r=await fetch('/health');const d=await r.json();el('total').textContent=(d.total_jobs||0).toLocaleString()+' 条记录';el('status').textContent='实时在招 '+((d.by_status||{}).open||0)+' 条 · 已连接生命周期库'}catch(e){el('status').textContent='暂时无法连接服务'}}
function draw(items){const box=el('results'); if(!items.length){box.innerHTML='<div class="empty">没有找到匹配结果，换一个更宽泛的关键词试试。</div>';return}box.innerHTML=items.map((j,i)=>`<article class="job"><h3>${esc(j.title)} ${j.lifecycle_status==='open'?'<span class="badge">实时在招</span>':'<span class="badge" style="background:#f1f2f5;color:#667085">历史参考</span>'}</h3><div class="meta">${esc(j.company)} · ${esc(j.job_group)} · ${esc(j.employment_kind)} · ${esc(j.campus_cycle)}</div><p>${esc(j.excerpt).slice(0,250)}…</p><button data-index="${i}">选择并匹配</button> <a href="${esc(j.source_url)}" target="_blank" rel="noopener">查看官方来源 ↗</a></article>`).join('');box.querySelectorAll('button').forEach(b=>b.onclick=()=>{selected=items[Number(b.dataset.index)];el('matchResult').style.display='block';el('matchResult').textContent='已选择：'+selected.title+'\n粘贴简历后点击“生成匹配建议”。';window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})})}
el('searchForm').onsubmit=async e=>{e.preventDefault();const box=el('results');box.innerHTML='<div class="empty">正在检索官方岗位库…</div>';try{const p=new URLSearchParams({query:el('query').value,scope:el('scope').value,limit:'20'});const r=await fetch('/api/jobs/search?'+p);if(!r.ok)throw new Error('搜索失败');draw(await r.json())}catch(err){box.innerHTML='<div class="empty">检索暂不可用，请稍后重试。</div>'}};
el('match').onclick=async()=>{const out=el('matchResult'),resume=el('resume').value.trim();out.style.display='block';if(!selected){out.textContent='请先从左侧选择一个岗位。';return}if(!resume){out.textContent='请先粘贴简历或项目经历。';return}out.textContent='正在分析…';try{const r=await fetch('/api/jobs/match',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:selected.id,resume_text:resume})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'匹配失败');const m=d.match||{};out.textContent=`投递状态：${d.application_notice||'请核验'}\n匹配结果：${JSON.stringify(m,null,2)}\n\n届别建议：${JSON.stringify(d.cycle_guidance||{},null,2)}`}catch(err){out.textContent='分析暂不可用：'+err.message}};
health();
</script></body></html>"""


def create_career_portal_app(components: PlatformComponents):
    app = create_platform_app(components)

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    def candidate_portal() -> str:
        return PORTAL_HTML

    return app
