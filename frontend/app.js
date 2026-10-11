const $ = (id) => document.getElementById(id);
let csrf = '', user = null, page = 1, total = 0, activeDetail = null, editingSubscription = null, subscriptionFilters = {};
const selected = new Set();
const labels = {title:'标题',address:'地址',area_m2:'面积',raw_amount:'原价',period_basis:'价格周期',registration_deadline:'报名截止',auction_deadline:'竞价截止',status:'状态',deposit:'保证金',project_code:'项目编号',environment:'所在环境',property_type:'物业类型',disclosure_deadline:'信息披露截止',operation:'经营用途',price_kind:'价格性质',city:'城市',district:'区县',keyword:'关键词',registration_open:'报名状态',area_m2_min:'面积下限',area_m2_max:'面积上限',first_year_monthly_min:'月租下限',first_year_monthly_max:'月租上限'};
const states = {open:'报名入口开放',closed:'已截止',failed:'流标',sold:'已成交',withdrawn:'撤回',unknown:'待核实'};
const sourceStates = {healthy:'本轮扫描完成',partial:'有限覆盖',blocked:'访问受阻',degraded:'采集异常',pending_validation:'待核验'};
const jobStates = {queued:'待执行',running:'执行中',retry_wait:'等待重试',complete:'完成',failed:'失败'};
const jobKinds = {front:'首页检查',backfill:'分页回扫',details:'详情复查'};
const noticeKinds = {new:'新增公告',changed:'公告条件变化',status_changed:'状态变化',deadline_extended:'报名延期',price_drop:'同口径降价',registration_reminder:'报名截止提醒'};
const kinds = {starting_bid:'起始价',asking:'挂牌价',sale:'成交价'};
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (value) => value == null ? '待确认' : Number(value).toLocaleString('zh-CN', {maximumFractionDigits:2});
const date = (value) => value ? new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}) : '待确认';
function toast(msg){$('toast').textContent=msg;$('toast').hidden=false;setTimeout(()=>$('toast').hidden=true,4500);}
async function api(path, options={}){
 const r=await fetch('/api/v1'+path,{...options,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...options.headers}});
 let data=await r.json();
 if(!r.ok){if(r.status===401){$('workspace').hidden=true;$('login').hidden=false;}throw new Error(typeof data.detail==='string'?data.detail:'请求未通过校验，请检查输入');}
 return data;
}
function filters(){
 const data=Object.fromEntries(new FormData($('filter-form')));
 for(const key of Object.keys(data)){if(data[key]==='')delete data[key];else if(key.endsWith('_min')||key.endsWith('_max'))data[key]=Number(data[key]);}
 data.registration_open=$('filter-form').elements.registration_open.checked;
 return data;
}
async function boot(){
 try{user=await api('/auth/me');csrf=user.csrf;$('login').hidden=true;$('workspace').hidden=false;$('user-label').textContent=user.username;$('mode').textContent=user.mode==='live'?'LIVE':'DEMO';$('demo-banner').hidden=user.mode==='live';await refresh();}
 catch(e){$('login').hidden=false;$('workspace').hidden=true;}
}
async function refresh(){await Promise.all([loadListings(),loadSources(),loadNotices(),loadSubscriptions()]);}
async function loadListings(){
 const data=await api('/listings/search',{method:'POST',body:JSON.stringify({filters:filters(),include_unknown:$('include-unknown').checked,page,limit:24,sort:$('sort').value})});
 total=data.total;$('stat-count').textContent=total;$('results-label').textContent=`找到 ${total} 条候选`;$('page-number').textContent=`${page} / ${Math.max(1,Math.ceil(total/24))}`;$('prev').disabled=page===1;$('next').disabled=page*24>=total;
 $('cards').innerHTML=data.items.length?data.items.map(r=>`<article class="card"><div class="card-header"><label class="check"><input type="checkbox" data-select="${r.id}" ${selected.has(r.id)?'checked':''}>比较</label><span>${esc(r.source_id==='nongjy'?'农交云':'温州职业技术学院')}</span><span class="badge ${r.match.verdict==='unknown'?'warn':''}">${r.match.verdict==='unknown'?'条件待确认':esc(states[r.status]||'状态待核实')}</span></div><h3>${esc(r.title)}</h3><p class="card-address">${esc(r.address||'地址待核实')}</p><div class="card-metrics"><div class="metric"><small>面积</small><strong>${money(r.area_m2)}</strong><span> ㎡</span></div><div class="metric"><small>${esc(kinds[r.price_kind]||'原价')} · ${r.period_basis==='first_year'?'年租':r.period_basis==='monthly'?'月租':'周期待确认'}</small><strong>${money(r.raw_amount)}</strong><span> 元</span></div></div><div class="card-footer"><span>报名截止 ${esc(date(r.registration_deadline))}</span><button class="link" data-detail="${r.id}">查看依据 ↗</button></div></article>`).join(''):'<div class="empty"><h3>当前没有候选</h3><p>可调整筛选条件，或在来源健康页检查采集覆盖。尚未同步时不代表没有新房源。</p></div>';
}
async function loadSources(){
 if(user.role==='admin'){const alerts=await api('/source-alerts');$('source-alerts').innerHTML=alerts.length?`<article class="stack-item"><span class="badge warn">${alerts.length} 个来源异常</span><p>异常来源需核验；受阻或重试耗尽的任务可能已暂停。</p>${alerts.map(a=>`<p class="error">${esc(a.source_id)}：${esc(a.error)}</p>`).join('')}</article>`:'';}else{$('source-alerts').innerHTML='';}

 const rows=await api('/sources');const successes=rows.filter(s=>s.last_success_at);$('stat-sources').textContent=successes.length;
 $('coverage-label').textContent=successes.length?`${successes.length} 个来源有扫描记录`:'来源尚未完成同步';
 $('sources').innerHTML=rows.map(s=>`<article class="stack-item"><span class="badge ${s.status==='healthy'?'':'warn'}">${esc(sourceStates[s.status]||s.status)}</span><h3>${esc(s.name)}</h3><p class="muted">最近成功：${esc(date(s.last_success_at))} · ${esc(s.coverage||'覆盖未验证')}</p>${s.detail_last_success_at?`<p class="muted">最近详情复查：${esc(date(s.detail_last_success_at))} · 核验 ${esc(s.detail_checked)} 条</p>`:''}${s.job?`<p class="muted">最近任务：${esc(jobKinds[s.job.kind]||s.job.kind)} · ${esc(jobStates[s.job.state]||s.job.state)} · 已尝试${esc(s.job.attempts)}次${s.job.retry_at?' · 重试时间：'+esc(date(s.job.retry_at)):''}</p>`:''}${s.error?`<p class="error">${esc(s.error)}</p>`:''}<p class="muted">持续监测：${s.enabled?'启用':'关闭'} · ${s.id==='wzcqpt'?'适配器待实现':'已提供HTML规则；附件待补强'}</p>${user.role==='admin'&&s.id!=='wzcqpt'?`<div class="actions"><button class="secondary" data-source-run="${esc(s.id)}">同步一次</button><button class="secondary" data-source-backfill="${esc(s.id)}">续扫一页</button><button class="secondary" data-source-details="${esc(s.id)}">复查活跃详情</button><button class="link" data-source-toggle="${esc(s.id)}" data-enabled="${s.enabled}">${s.enabled?'暂停':'启用'}定时监测</button></div>`:''}</article>`).join('');
}
async function loadSubscriptions(){
 const rows=await api('/subscriptions');$('subscriptions').innerHTML=rows.length?rows.map(s=>`<article class="stack-item"><span class="badge">${s.enabled?'启用':'暂停'}</span><h3>${esc(s.name)}</h3><p class="muted">${esc(Object.entries(s.filters).filter(([k,v])=>v!==false&&v!==null).map(([k,v])=>`${labels[k]||k}：${changeValue(k,v)}`).join(' / ')||'所有条件不限')}<br>未知条件：${s.unknown_policy==='exclude'?'排除':'待确认候选'}<br>报名提醒：${s.reminder_hours.length?s.reminder_hours.map(h=>`提前 ${h} 小时`).join(' / '):'关闭'}</p><div class="actions"><button class="secondary" data-sub-edit="${s.id}">编辑设置</button><button class="secondary" data-sub-toggle="${s.id}">${s.enabled?'暂停':'恢复'}</button></div></article>`).join(''):'<div class="empty">还没有订阅。选择筛选条件后点击“保存为订阅”。</div>';
 window.currentSubscriptions=rows;
}
function changeValue(key, value){
 if(value==null)return '待确认';
 if(key==='status')return states[value]||'待核实';
 if(key==='registration_open')return value?'仅可报名':'不限';
 if(key==='property_type')return {shop:'商铺 / 店面',commercial_unit:'商业单元',office:'办公',warehouse:'厂房 / 仓库',apartment:'公寓'}[value]||'待确认';
 if(key==='environment')return {campus:'校园',apartment_building:'公寓楼',street:'沿街',market:'市场'}[value]||'待确认';
 if(key==='operation')return {coffee_beverage:'咖啡 / 饮品',restaurant:'餐饮',retail:'零售'}[value]||'待确认';
 if(key==='price_kind')return kinds[value]||'待确认';
 if(key==='period_basis')return {first_year:'首年租金',monthly:'月租'}[value]||'待确认';
 if(key.endsWith('_deadline'))return date(value);
 return String(value);
}
async function loadNotices(){
 const rows=await api('/notifications');
 const [receipts,health]=await Promise.all([api('/email-deliveries'),api('/health/ready')]);
 $('stat-email').textContent={configured:'已配置',disabled:'未配置',invalid_configuration:'配置错误'}[health.external_notifications]||'待核验';
 const deliveryStates={queued:'等待发送',sending:'正在发送',retry_wait:'等待重试',accepted:'邮件服务器已接受',dead_letter:'发送失败，待处理',ambiguous:'结果不明，待人工核验',cancelled:'已取消'};
 $('email-deliveries').innerHTML=receipts.length?receipts.map(r=>`<article class="stack-item"><span class="badge">${esc(deliveryStates[r.state]||r.state)}</span><p>通知 #${esc(r.notice_id)} · 尝试 ${esc(r.attempts)} 次${r.retry_at?' · 下次重试：'+esc(date(r.retry_at)):''}</p>${r.error?`<p class="muted">${esc(r.error)}</p>`:''}</article>`).join(''):'<p class="muted">暂无邮件发送记录；未配置时仅使用站内收件箱。</p>';$('stat-notices').textContent=rows.filter(r=>!r.read&&r.state!=='cancelled').length;
 $('notifications').innerHTML=rows.length?rows.map(r=>`<article class="stack-item"><span class="badge ${r.state==='cancelled'||r.match.verdict==='unknown'?'warn':''}">${r.state==='cancelled'?'提醒已作废':r.notice_class==='status_update'?'原候选变化':r.match.verdict==='unknown'?'条件待确认':r.notice_class==='deadline_reminder'?'报名提醒':'明确匹配'} · ${r.read?'已读':'未读'}</span><h3>${esc(r.title)}</h3><p class="muted">${esc(date(r.created_at))} · ${esc(noticeKinds[r.kind]||r.kind)} · ${esc({queued:'等待处理',accepted:'已入站内收件箱',cancelled:'已作废'}[r.state]||r.state)}</p>${r.kind==='registration_reminder'?`<p>已进入提前 ${esc(r.lead_hours)} 小时提醒窗口。报名截止：${esc(date(r.registration_deadline))}</p><p class="muted">最近核验：${esc(date(r.last_checked_at))}</p>`:''}${(r.changes||[]).length?`<p class="muted">${r.changes.map(c=>`${esc(labels[c.field]||c.field)}：${esc(changeValue(c.field,c.before))} → ${esc(changeValue(c.field,c.after))}`).join('<br>')}</p>`:''}<div class="actions"><button class="secondary" data-detail="${r.listing_id}">查看详情</button><button class="link" data-read="${r.id}">标记已读</button></div></article>`).join(''):'<div class="empty">暂无提醒。保存订阅后，后续采集变化和报名截止提醒会出现在这里。</div>';
}

async function showDetail(id){
 const r=await api('/listings/'+id);activeDetail=r;
 const pairs=[['地址',r.address||'待核实'],['面积',`${money(r.area_m2)} ㎡`],['原始价格',`${money(r.raw_amount)} 元 · ${kinds[r.price_kind]}`],['月租基准',`${money(r.first_year_monthly)}${r.first_year_monthly?' 元/月':''}`],['单位面积月租',`${money(r.unit_monthly)}${r.unit_monthly?' 元/㎡/月':''}`],['报名截止',date(r.registration_deadline)],['竞价截止',date(r.auction_deadline)],['保证金',`${money(r.deposit)} 元`],['最后核验',date(r.last_checked_at)]];
 $('detail-body').innerHTML=`<span class="badge">${esc(states[r.status]||'状态待核实')}</span><h2>${esc(r.title)}</h2><p class="muted">来源记录 #${r.id} · <a href="${esc(r.source_url)}" target="_blank" rel="noopener noreferrer">打开原始公告 ↗</a></p><div class="detail-grid">${pairs.map(([k,v])=>`<div><small>${esc(k)}</small>${esc(v)}</div>`).join('')}</div>${r.formula?`<p class="muted">换算：${esc(r.formula)}；税费等成本未完整核实。</p>`:''}<div class="warning">${(r.warnings||[]).map(esc).join('<br>')}</div><h3>关键字段依据</h3>${r.evidence.map(e=>`<div class="evidence"><strong>${esc(labels[e.field]||e.field)}</strong>${esc(e.quote)}</div>`).join('')}<h3>跟进记录</h3><form id="followup-form" class="followup-form"><select name="status">${['未查看','已查看','待联系','已联系','预约看铺','放弃','已成交'].map(s=>`<option ${r.followup?.status===s?'selected':''}>${s}</option>`).join('')}</select><label class="check"><input name="favorite" type="checkbox" ${r.followup?.favorite?'checked':''}>收藏该铺位</label><textarea name="note" rows="3" maxlength="3000" placeholder="联系情况、看铺记录或放弃原因">${esc(r.followup?.note||'')}</textarea><button class="primary">保存跟进</button></form><h3>版本历史 · ${r.versions.length}</h3><p class="muted">${r.versions.map(v=>esc(date(v.created_at))).join(' / ')}</p><details><summary>查看保存的原文文本</summary><p class="source-text">${esc(r.source_text)}</p></details>`;
 $('detail').showModal();
 $('followup-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{await api(`/listings/${r.id}/followup`,{method:'PATCH',body:JSON.stringify({status:f.elements.status.value,note:f.elements.note.value,favorite:f.elements.favorite.checked})});toast('跟进记录已保存');}catch(e){toast(e.message);}};
}
$('login-form').onsubmit=async e=>{e.preventDefault();try{const data=Object.fromEntries(new FormData(e.target));await api('/auth/login',{method:'POST',body:JSON.stringify(data)});e.target.reset();await boot();}catch(e){$('login-error').textContent=e.message;}};
$('logout').onclick=async()=>{await api('/auth/logout',{method:'POST'});csrf='';await boot();};
$('filter-form').onsubmit=e=>{e.preventDefault();page=1;loadListings().catch(e=>toast(e.message));};
$('filter-form').onreset=()=>setTimeout(()=>{page=1;loadListings().catch(e=>toast(e.message));},0);
$('prev').onclick=()=>{if(page>1){page--;loadListings().catch(e=>toast(e.message));}};
$('next').onclick=()=>{if(page*24<total){page++;loadListings().catch(e=>toast(e.message));}};
$('close-detail').onclick=()=>$('detail').close();
function openSubscription(subscription=null){
 editingSubscription=subscription;
 subscriptionFilters=subscription?subscription.filters:filters();
 const f=$('subscription-form');f.elements.name.value=subscription?.name||'';
 f.elements.unknown_policy.value=subscription?.unknown_policy||'review_digest';
 f.elements.reminder_hours.value=(subscription?.reminder_hours||[72,24]).join(', ');
 $('subscription-title').textContent=subscription?'编辑订阅设置':'保存当前筛选';
 $('submit-subscription').textContent=subscription?'保存设置':'保存订阅';
 $('subscription-dialog').showModal();
}
$('save-subscription').onclick=()=>openSubscription();
$('cancel-subscription').onclick=()=>$('subscription-dialog').close();
$('subscription-form').onsubmit=async e=>{
 e.preventDefault();
 try{
  const f=e.target;const text=f.elements.reminder_hours.value.trim();
  const values=text?text.replace(/，/g,',').split(',').map(v=>v.trim()):[];
  if(values.some(v=>!/^\d+$/.test(v)))throw new Error('提醒时间请填写整数小时，用逗号分隔；留空关闭');
  const reminder_hours=values.map(Number);
  const body={name:f.elements.name.value,unknown_policy:f.elements.unknown_policy.value,filters:subscriptionFilters,reminder_hours,enabled:editingSubscription?.enabled??true};
  const r=await api('/subscriptions'+(editingSubscription?'/'+editingSubscription.id:''),{method:editingSubscription?'PATCH':'POST',body:JSON.stringify(body)});
  $('subscription-dialog').close();toast(editingSubscription?'订阅设置已更新':`订阅已保存：历史明确匹配 ${r.baseline.pass} 条，待确认 ${r.baseline.unknown} 条`);await loadSubscriptions();await loadNotices();
 }catch(e){toast(e.message);}
};
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b)return;
 try{
 if(b.dataset.view){document.querySelectorAll('nav button').forEach(n=>n.classList.toggle('active',n===b));for(const v of ['listings','subscriptions','notifications','sources'])$('view-'+v).hidden=v!==b.dataset.view;$('page-title').textContent=b.textContent.trim().slice(1).trim();await refresh();}
 if(b.dataset.detail)await showDetail(b.dataset.detail);
 if(b.dataset.read){await api('/notifications/'+b.dataset.read,{method:'PATCH'});await loadNotices();}
 if(b.dataset.sourceRun){b.disabled=true;await api('/sources/'+b.dataset.sourceRun+'/runs',{method:'POST'});toast('任务已入队，请稍后查看来源健康');b.disabled=false;}
 if(b.dataset.sourceBackfill){await api('/sources/'+b.dataset.sourceBackfill+'/runs?kind=backfill',{method:'POST'});toast('续扫任务已入队');}
 if(b.dataset.sourceDetails){await api('/sources/'+b.dataset.sourceDetails+'/runs?kind=details',{method:'POST'});toast('活跃详情复查已入队');await loadSources();}
 if(b.dataset.sourceToggle){await api('/sources/'+b.dataset.sourceToggle,{method:'PATCH',body:JSON.stringify({enabled:b.dataset.enabled!=='true'})});await loadSources();}
 if(b.dataset.subEdit)openSubscription(window.currentSubscriptions.find(s=>String(s.id)===b.dataset.subEdit));
 if(b.dataset.subToggle){const s=window.currentSubscriptions.find(s=>String(s.id)===b.dataset.subToggle);await api('/subscriptions/'+s.id,{method:'PATCH',body:JSON.stringify({...s,enabled:!s.enabled})});await loadSubscriptions();}
 }catch(e){b.disabled=false;toast(e.message);}
});
boot();

document.addEventListener('change', e=>{
 if(!e.target.dataset.select)return;
 const id=Number(e.target.dataset.select);
 if(e.target.checked){if(selected.size>=5){e.target.checked=false;toast('最多比较5条');return;}selected.add(id);}else selected.delete(id);
 $('compare-selected').textContent=`比较已选（${selected.size}）`;
});
$('compare-selected').onclick=async()=>{
 if(selected.size<2){toast('请勾选2–5条候选');return;}
 try{
  const result=await api('/comparisons',{method:'POST',body:JSON.stringify({listing_ids:[...selected]})});
  const fields=[['address','地址'],['area_m2','面积 · ㎡'],['price_kind','价格性质'],['raw_amount','原价 · 元'],['period_basis','价格周期'],['first_year_monthly','月租基准 · 元'],['unit_monthly','元/㎡/月'],['formula','换算依据'],['registration_deadline','报名截止']];
  $('detail-body').innerHTML=`<h2>候选比较</h2><p class="warning">${esc(result.warning)}</p><div class="comparison-scroll"><table class="comparison"><thead><tr><th>字段</th>${result.items.map(r=>`<th>${esc(r.title)}</th>`).join('')}</tr></thead><tbody>${fields.map(([key,label])=>`<tr><th>${esc(label)}</th>${result.items.map(r=>`<td>${esc(key==='price_kind'?(kinds[r[key]]||'待确认'):key==='period_basis'?({first_year:'首年租金',monthly:'月租'}[r[key]]||'待确认'):key==='registration_deadline'?date(r[key]):(r[key]??'待确认'))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  $('detail').showModal();
 }catch(e){toast(e.message);}
};
