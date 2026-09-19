"""UI additions for the grounded CareerAgent planning workflow."""

from __future__ import annotations

from .career_portal_release import CAREER_PORTAL_RELEASE_HTML


_STYLE = """
.copilot{margin-top:16px;padding:16px}.copilot-grid{display:grid;grid-template-columns:1fr 1.4fr;gap:12px}.copilot-output{white-space:pre-wrap;background:#f8faff;border:1px solid var(--line);border-radius:10px;padding:12px;min-height:110px}.fresh{margin:14px 0;padding:12px 14px;border-left:4px solid var(--brand);color:#31415f}.fresh b{color:var(--ink)}.citation{display:block;padding:7px 0;color:var(--brand);font-size:13px;text-decoration:none}.citation:hover{text-decoration:underline}.profile{margin-top:16px;padding:16px}.profile-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.profile-status{font-size:12px;color:var(--muted);margin-top:8px}@media(max-width:700px){.profile-grid{grid-template-columns:1fr}}@media(max-width:980px){.copilot-grid{grid-template-columns:1fr}}
"""

_PANEL = """
<section class="card fresh" id="freshness">\u6b63\u5728\u8bfb\u53d6\u5c97\u4f4d\u65f6\u6548\u4fe1\u606f\u2026</section>
<section class="card profile"><h2>\u4e2a\u4eba\u504f\u597d\u4e0e\u901a\u77e5</h2><p class="notice">\u504f\u597d\u4ec5\u4fdd\u5b58\u5728\u5f53\u524d\u90e8\u7f72\u7684\u6570\u636e\u5e93\u4e2d\u3002\u586b\u5199\u90ae\u7bb1\u540e\uff0c\u5df2\u4fdd\u5b58\u7684\u5c97\u4f4d\u8ba2\u9605\u53ef\u5728\u540c\u6b65\u540e\u751f\u6210\u90ae\u4ef6\u6458\u8981\uff1b\u5728 SMTP \u672a\u914d\u7f6e\u65f6\u53ea\u4f1a\u8bb0\u5f55\u9884\u89c8\uff0c\u4e0d\u4f1a\u4f2a\u9020\u201c\u5df2\u53d1\u9001\u201d\u3002</p><div class="profile-grid"><input id="profileEmail" type="email" placeholder="\u63a5\u6536\u901a\u77e5\u7684\u90ae\u7bb1\uff08\u53ef\u9009\uff09"><input id="profileCycle" placeholder="\u6821\u62db\u5c4a\u522b\uff0c\u4f8b\u5982 2027_autumn"><select id="profileKind"><option value="">\u4e0d\u9650\u5c97\u4f4d\u7c7b\u578b</option><option value="campus">\u6821\u62db</option><option value="internship">\u5b9e\u4e60</option><option value="experienced">\u793e\u62db</option></select></div><button id="profileSave" class="secondary" type="button" style="margin-top:8px">\u4fdd\u5b58\u504f\u597d</button><div id="profileStatus" class="profile-status"></div></section>
<section class="card copilot"><h2>AI \u6c42\u804c\u89c4\u5212\u52a9\u624b</h2><p class="notice">\u57fa\u4e8e\u5f53\u524d\u5c97\u4f4d\u3001\u7b80\u5386\u5173\u952e\u8bcd\u548c\u53ef\u89e3\u91ca\u7684\u6280\u80fd\u7f3a\u53e3\u751f\u6210\u884c\u52a8\u8ba1\u5212\uff1b\u6bcf\u6761\u63a8\u8350\u5747\u53ef\u56de\u5230\u5b98\u65b9\u5c97\u4f4d\u94fe\u63a5\u6838\u9a8c\u3002</p><div class="copilot-grid"><div><input id="copilotRole" placeholder="\u76ee\u6807\u65b9\u5411\uff0c\u4f8b\u5982\uff1a\u540e\u7aef\u5f00\u53d1 / \u4ea7\u54c1\u7ecf\u7406"><input id="copilotLocation" style="margin-top:8px" placeholder="\u610f\u5411\u57ce\u5e02\uff08\u53ef\u9009\uff09"><textarea id="copilotMessage" style="margin-top:8px" placeholder="\u544a\u8bc9\u52a9\u624b\u4f60\u7684\u76ee\u6807\u3001\u5c4a\u522b\u6216\u56f0\u60d1\uff0c\u4f8b\u5982\uff1a27 \u5c4a\uff0c\u60f3\u6295\u5317\u4eac AI \u7b97\u6cd5\u5c97\uff0c\u672c\u5468\u8be5\u51c6\u5907\u4ec0\u4e48\uff1f"></textarea><label class="notice" style="display:block;margin-top:8px"><input id="copilotUseLlm" type="checkbox"> \u4f7f\u7528\u5df2\u914d\u7f6e\u7684\u5916\u90e8\u6a21\u578b\u8fdb\u884c\u5de5\u5177\u8c03\u7528\uff08\u4f1a\u53d1\u9001\u672c\u6b21\u95ee\u9898\u53ca\u7b80\u5386\u6587\u672c\uff1b\u672a\u914d\u7f6e\u65f6\u81ea\u52a8\u4f7f\u7528\u672c\u5730\u89c4\u5219\u65b9\u6848\uff09</label><button id="copilotRun" type="button" style="margin-top:8px">\u751f\u6210\u672c\u8f6e\u6c42\u804c\u8ba1\u5212</button></div><div><div id="copilotOutput" class="copilot-output">\u586b\u5199\u76ee\u6807\u540e\uff0c\u52a9\u624b\u4f1a\u7ed9\u51fa\u5c97\u4f4d\u4f9d\u636e\u3001\u6280\u80fd\u7f3a\u53e3\u548c\u4e0b\u4e00\u6b65\u884c\u52a8\u3002</div><div id="copilotCitations"></div></div></div></section>
"""

_SCRIPT = """
async function loadFreshness(){
  try{
    const d=await fetch('/api/career/freshness').then(r=>r.json());
    el('freshness').replaceChildren();
    const b=document.createElement('b');
    b.textContent=`\u5b9e\u65f6\u53ef\u6295 ${d.open_jobs} \u4e2a`;
    el('freshness').append(b,document.createTextNode(` \u00b7 24 \u5c0f\u65f6\u5185\u6838\u9a8c ${d.open_verified_last_24h} \u4e2a \u00b7 \u5f85\u590d\u6838 ${d.unverified_jobs} \u4e2a\u3002${d.disclosure}`));
  }catch{el('freshness').textContent='\u6682\u65f6\u65e0\u6cd5\u8bfb\u53d6\u5c97\u4f4d\u65f6\u6548\u4fe1\u606f\u3002'}
}
async function loadProfile(){
  try{
    const r=await fetch('/api/career/profile');const p=await r.json();if(!r.ok)throw Error(p.detail||'\u8bfb\u53d6\u5931\u8d25');
    el('profileEmail').value=p.email||'';el('profileCycle').value=p.campus_cycle||'';el('profileKind').value=p.employment_kind||'';
    if(!el('copilotRole').value)el('copilotRole').value=(p.target_roles||[]).join(' / ');
    if(!el('copilotLocation').value)el('copilotLocation').value=(p.target_locations||[]).join(' / ');
  }catch{el('profileStatus').textContent='\u504f\u597d\u6682\u65f6\u65e0\u6cd5\u8bfb\u53d6\u3002'}
}
function profileList(value){return value.split(/[\\/,，、]/).map(x=>x.trim()).filter(Boolean)}
async function saveProfile(){
  const status=el('profileStatus');status.textContent='\u6b63\u5728\u4fdd\u5b58\u2026';
  try{
    const r=await fetch('/api/career/profile',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:el('profileEmail').value.trim(),target_roles:profileList(el('copilotRole').value),target_locations:profileList(el('copilotLocation').value),campus_cycle:el('profileCycle').value.trim(),employment_kind:el('profileKind').value})});
    const p=await r.json();if(!r.ok)throw Error(p.detail||'\u4fdd\u5b58\u5931\u8d25');status.textContent='\u5df2\u4fdd\u5b58\u3002';
  }catch(error){status.textContent=`\u4fdd\u5b58\u5931\u8d25\uff1a${error.message}`}
}
async function dispatchSubscription(id,name){
  try{const r=await fetch(`/api/career/subscriptions/${id}/dispatch`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const d=await r.json();if(!r.ok)throw Error(d.detail||'\u5904\u7406\u5931\u8d25');alert(`${name}\uff1a${d.delivery.status}。${d.delivery.detail}`)}catch(error){alert(`\u8ba2\u9605\u5904\u7406\u5931\u8d25\uff1a${error.message}`)}}
const baseLoadWorkspace=loadWorkspace;
loadWorkspace=async function(){
  await baseLoadWorkspace();
  try{const s=await fetch('/api/career/subscriptions').then(r=>r.json());const subs=el('subscriptions');subs.replaceChildren();if(!s.length){subs.textContent='\u4fdd\u5b58\u4e00\u4e2a\u641c\u7d22\u6761\u4ef6\uff0c\u540e\u7eed\u53ef\u4f5c\u4e3a\u6bcf\u65e5\u540c\u6b65\u540e\u7684\u7b5b\u9009\u6a21\u677f\u3002';return}s.forEach(x=>{const row=document.createElement('div');row.className='track';const label=document.createElement('span');label.textContent=`${x.name}\uff1a${x.query||'\u5168\u90e8\u5c97\u4f4d'}`;const button=document.createElement('button');button.className='small secondary';button.style.marginLeft='8px';button.textContent='\u751f\u6210\u90ae\u4ef6\u6458\u8981';button.onclick=()=>dispatchSubscription(x.id,x.name);row.append(label,button);subs.append(row)})}catch{}
};
el('profileSave').onclick=saveProfile;loadProfile();loadWorkspace();
function copilotText(plan){
  const gaps=plan.skills.priority_gaps.length?plan.skills.priority_gaps.join('\u3001'):'\u6682\u672a\u8bc6\u522b\u51fa\u660e\u786e\u6280\u80fd\u7f3a\u53e3';
  return `${plan.summary}\\n\\n\u4e0b\u4e00\u6b65\uff1a\\n${plan.actions.map((x,i)=>`${i+1}. ${x}`).join('\\n')}\\n\\n\u5df2\u8986\u76d6\u6280\u80fd\uff1a${plan.skills.covered.join('\u3001')||'\u8bf7\u7c98\u8d34\u7b80\u5386\u4ee5\u8bc6\u522b'}\\n\u4f18\u5148\u8865\u9f50\uff1a${gaps}\\n\\n${plan.boundary}`;
}
async function runCopilot(){
  const output=el('copilotOutput'),citations=el('copilotCitations');
  output.textContent='\u6b63\u5728\u68c0\u7d22\u5c97\u4f4d\u5e76\u751f\u6210\u8ba1\u5212\u2026';citations.replaceChildren();
  try{
    const r=await fetch('/api/career/copilot/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_role:el('copilotRole').value.trim(),target_location:el('copilotLocation').value.trim(),message:el('copilotMessage').value.trim(),resume_text:el('resume').value.trim(),scope:el('scope').value,use_llm:el('copilotUseLlm').checked})});
    const d=await r.json();if(!r.ok)throw Error(d.detail||'\u751f\u6210\u5931\u8d25');
    output.textContent=copilotText(d.plan);
    d.plan.citations.forEach(item=>{const a=document.createElement('a');a.className='citation';a.href=item.source_url;a.target='_blank';a.rel='noreferrer';a.textContent=`${item.status==='open'?'\u5b9e\u65f6':'\u5386\u53f2\u53c2\u8003'} \u00b7 ${item.company}\u2014${item.title}\uff08\u5339\u914d ${item.match_score||'-'}\uff09`;citations.append(a)});
  }catch(error){output.textContent=`\u751f\u6210\u5931\u8d25\uff1a${error.message}`}
}
el('copilotRun').onclick=runCopilot;loadFreshness();
"""


CAREER_PORTAL_COPILOT_HTML = (
    CAREER_PORTAL_RELEASE_HTML.replace("</style>", _STYLE + "</style>")
    .replace("</main><script>", _PANEL + "</main><script>")
    .replace("</script>", _SCRIPT + "</script>")
)
