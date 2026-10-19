const $ = (id) => document.getElementById(id);
let sessionGeneration=0;
let demoScenario=null,demoRouteIndex=-1,demoRouteBusy=false;
let noticePage=1,emailPage=1,digestPage=1,reviewPage=1,incidentPage=1,incidentEmailPage=1;
let csrf = '', user = null, page = 1, total = 0, activeDetail = null, editingSubscription = null, subscriptionFilters = {};
const selected = new Set();
const listingCache = new Map();
let appliedQuery={filters:{registration_open:false},include_unknown:true,sort:'newest',view:'all'}, listingRequest=0;
const labels = {disclosed_use:'公告用途原文（许可待核验）',lease_term_text:'租期原文',free_rent_text:'免租期原文',rent_notes:'租金备注原文',title:'标题',address:'地址',area_m2:'面积',raw_amount:'原价',period_basis:'价格周期',registration_deadline:'报名截止',auction_deadline:'竞价截止',status:'状态',deposit:'保证金',project_code:'项目编号',environment:'所在环境',property_type:'物业类型',disclosure_deadline:'信息披露截止',operation:'经营用途',price_kind:'价格性质',city:'城市',district:'区县',keyword:'关键词',registration_open:'报名状态',area_m2_min:'面积下限',area_m2_max:'面积上限',first_year_monthly_min:'月租下限',first_year_monthly_max:'月租上限'};
const states = {open:'报名入口开放',closed:'已截止',failed:'流标',sold:'已成交',withdrawn:'撤回',unknown:'待核实'};
const sourceStates = {healthy:'本轮扫描完成',partial:'有限覆盖',blocked:'访问受阻',degraded:'采集异常',pending_validation:'待核验'};
const jobStates = {queued:'待执行',running:'执行中',retry_wait:'等待重试',complete:'完成',failed:'失败'};
const jobKinds = {import:'链接导入',front:'首页检查',backfill:'分页回扫',details:'详情复查'};
const noticeKinds = {new:'新增公告',changed:'公告条件变化',status_changed:'状态变化',deadline_extended:'报名延期',price_drop:'同口径降价',registration_reminder:'报名截止提醒'};
const kinds = {starting_bid:'起始价',asking:'挂牌价',sale:'成交价'};
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (value) => value == null ? '待确认' : Number(value).toLocaleString('zh-CN', {maximumFractionDigits:2});
const date = (value) => !value?'待确认':/^\d{4}-\d{2}-\d{2}$/.test(value)?value:Number.isNaN(new Date(value).getTime())?'时间待核实':new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
function registrationText(r){
 if(['closed','failed','sold','withdrawn'].includes(r.status))return states[r.status];
 const cutoff=r.registration_deadline?new Date(r.registration_deadline).getTime():NaN;
 if(Number.isFinite(cutoff)&&cutoff<=Date.now())return '报名期限已过';
 return r.status==='open'&&Number.isFinite(cutoff)?'报名期限内':'报名状态待核实';
}
function filterText(f){return Object.entries(f).filter(([k,v])=>v!==false&&v!==null&&v!=='').map(([k,v])=>`${labels[k]||k}：${changeValue(k,v)}`).join(' · ')||'所有条件不限';}
function draftQuery(){return {filters:filters(),include_unknown:$('include-unknown').checked,sort:$('sort').value,view:appliedQuery.view||'all'};}
function pendingFilters(){$('filter-pending').hidden=JSON.stringify(draftQuery())===JSON.stringify(appliedQuery);}
function renderQuickViews(){
 document.querySelectorAll('[data-quick-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.quickView===(appliedQuery.view||'all'))));
 $('quick-view-note').textContent=['favorites','following'].includes(appliedQuery.view)?'仅显示当前账号的收藏或待联系、已联系、预约看铺记录；保留已截止项方便收尾。仍与已应用筛选取交集，保存订阅不包含此视图。':'快捷视图只改变当前浏览范围；保存订阅时仅使用下方筛选条件。';
}
function renderSelection(){
 const visible=selected.size>0&&!$('view-listings').hidden;
 $('compare-tray').hidden=!visible;document.body.classList.toggle('has-selection',visible);
 $('selection-count').textContent=`已选 ${selected.size} / 5 条`;
 $('selection-items').innerHTML=[...selected].map(id=>`<button class="selection-chip" data-remove-selection="${id}" title="${esc(listingCache.get(id)?.title||'#'+id)}">${esc(listingCache.get(id)?.title||'#'+id)} <span aria-hidden="true">×</span><span class="sr-only">移出比较</span></button>`).join('');
 $('compare-selected').textContent=`比较已选（${selected.size}）`;$('compare-selected').disabled=selected.size<2;$('compare-tray-open').disabled=selected.size<2;
 document.querySelectorAll('[data-select]').forEach(el=>el.checked=selected.has(Number(el.dataset.select)));
}

function toast(msg){$('toast').textContent=msg;$('toast').hidden=false;setTimeout(()=>$('toast').hidden=true,4500);}
function clearWorkspace(){
 demoScenario=null;demoRouteIndex=-1;demoRouteBusy=false;$('demo-route').hidden=true;
 sessionGeneration++;documentPage=1;noticePage=emailPage=digestPage=reviewPage=incidentPage=incidentEmailPage=1;csrf='';user=null;activeDetail=null;editingSubscription=null;subscriptionFilters={};selected.clear();listingCache.clear();window.currentSubscriptions=[];listingRequest++;
 appliedQuery={filters:{registration_open:false},include_unknown:true,sort:'newest',view:'all'};renderQuickViews();
 for(const id of ['subscriptions','notifications','email-deliveries','detail-body','cards','filter-summary','source-alerts','digests','incidents','review-queue','sources','lease-result','document-reviews','incident-emails'])$(id).innerHTML='';
 for(const dialog of document.querySelectorAll('dialog'))if(dialog.open)dialog.close();
 for(const el of $('filter-form').elements){if(el.name){if(el.type==='checkbox')el.checked=false;else el.value='';}}
 $('include-unknown').checked=true;$('sort').value='newest';$('subscription-form').reset();$('preference-form').reset();$('lease-form').reset();$('document-form').reset();$('import-form').reset();for(const id of ['stat-count','stat-notices','stat-sources'])$(id).textContent='—';for(const v of ['listings','subscriptions','notifications','sources','review','tools'])$('view-'+v).hidden=v!=='listings';document.querySelectorAll('nav button').forEach(n=>n.classList.toggle('active',n.dataset.view==='listings'));$('page-title').textContent='候选铺位';renderSelection();
}
async function api(path, options={}){
 const generation=sessionGeneration;
 const r=await fetch('/api/v1'+path,{...options,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...options.headers}});
 let data=await r.json();
 if(generation!==sessionGeneration)throw new Error('会话已变更，请重新登录');
 if(!r.ok){if(r.status===401){clearWorkspace();$('workspace').hidden=true;$('login').hidden=false;}throw new Error(typeof data.detail==='string'?data.detail:'请求未通过校验，请检查输入');}
 return data;
}
function filters(){
 const data=Object.fromEntries(new FormData($('filter-form')));
 for(const key of Object.keys(data)){if(data[key]==='')delete data[key];}
 data.registration_open=$('filter-form').elements.registration_open.checked;
 return data;
}
async function boot(){
 try{user=await api('/auth/me');csrf=user.csrf;$('login').hidden=true;$('workspace').hidden=false;$('user-label').textContent=user.username;$('review-nav').hidden=$('import-form').hidden=$('document-upload-section').hidden=user.role!=='admin';$('incident-heading').hidden=$('incident-pagination').hidden=$('incident-email-section').hidden=user.role!=='admin';$('mode').textContent=user.mode==='live'?'LIVE':'DEMO';$('demo-banner').hidden=user.mode==='live';renderSelection();await refresh();await loadDemoRoute();}
 catch(e){if(!user){$('login').hidden=false;$('workspace').hidden=true;}else toast(e.message);}
}
async function refresh(){await Promise.all([loadListings(),loadSources(),loadNotices(),loadSubscriptions(),loadPreferences(),...(user.role==='admin'?[loadReview(),loadIncidents(),loadDocuments(),loadIncidentEmails()]:[])]);}
function renderListingRow(r){
 const source={nongjy:'农交云',wzpt:'温州职业技术学院',wzcqpt:'温州联合产权交易中心'}[r.source_id]||r.source_id;
 const status=registrationText(r);
 const uncertain=!['报名期限已过','已截止','流标','已成交','撤回'].includes(status)&&(r.match?.verdict==='unknown'||r.source_conflicts?.length>0||r.review_conflicts?.length>0||r.status==null||r.status==='unknown'||r.area_m2==null||r.raw_amount==null||r.registration_deadline==null||!['first_year','monthly'].includes(r.period_basis));
 const priceBasis=r.period_basis==='first_year'?'首年租金':r.period_basis==='monthly'?'月租':'周期待确认';
 const monthly=r.first_year_monthly!=null?`首年月租基准 ${money(r.first_year_monthly)} 元；税费等未完整核实`:'月租不可比：价格周期尚未核实';
 return `<article class="listing-row"><div class="listing-row-main"><div class="listing-row-kicker"><span>${esc(source)}</span><span class="listing-status ${status==='报名期限内'?'':'is-uncertain'}">${esc(status)}</span>${uncertain?'<span class="listing-status is-uncertain">条件待核实</span>':''}</div><h3><button type="button" class="listing-title" data-detail="${r.id}">${esc(r.title)}</button></h3><p class="listing-address">${esc(r.address||'地址待核实')}</p>${r.source_count>1?`<p class="listing-source-note">${r.source_count} 个已人工关联的出处${r.source_conflicts?.length?' · 来源字段冲突待核验':''}</p>`:''}</div><dl class="listing-row-facts"><div><dt>面积</dt><dd>${money(r.area_m2)} <small>㎡</small></dd></div><div><dt>${esc(kinds[r.price_kind]||'原价')} · ${priceBasis}</dt><dd>${money(r.raw_amount)} <small>元</small></dd></div><div><dt>报名截止</dt><dd class="deadline-value">${esc(date(r.registration_deadline))}</dd></div></dl><div class="listing-row-footer">${personalActions(r)}<span>${monthly}</span><span>最近核验 ${esc(date(r.last_checked_at))}</span><label class="listing-select"><input type="checkbox" data-select="${r.id}" ${selected.has(r.id)?'checked':''}>加入比较</label><button class="link" type="button" data-detail="${r.id}">查看依据 →</button></div></article>`;
}
async function loadListings(query=appliedQuery){
 const request=++listingRequest;
 const data=await api('/listings/search',{method:'POST',body:JSON.stringify({...query,page,limit:24})});
 if(request!==listingRequest)return;
 appliedQuery=query;renderQuickViews();data.items.forEach(r=>listingCache.set(r.id,r));
 for(const field of ['city','district'])$('options-'+field).innerHTML=[...new Set([...listingCache.values()].map(r=>r[field]).filter(Boolean))].sort().map(v=>`<option value="${esc(v)}"></option>`).join('');
 $('filter-summary').textContent='已应用：'+filterText(query.filters)+(query.include_unknown?' · 包含待确认':' · 排除待确认');pendingFilters();
 total=data.total;if(page>Math.max(1,Math.ceil(total/24))){page=1;return loadListings(query);}$('stat-count').textContent=total;$('results-label').textContent=`找到 ${total} 条候选`;$('page-number').textContent=`${page} / ${Math.max(1,Math.ceil(total/24))}`;$('prev').disabled=page===1;$('next').disabled=page*24>=total;
 $('cards').innerHTML=data.items.length?data.items.map(renderListingRow).join(''):`<div class="empty"><h3>${query.view==='all'?'当前没有候选':'这个快捷视图暂无候选'}</h3><p>${query.view==='all'?'可调整筛选条件，或在来源健康页检查采集覆盖。尚未同步时不代表没有新房源。':'可查看全部候选，或调整筛选条件。来源尚未同步完成时，结果不代表全站没有机会。'}</p>${query.view==='all'?'':'<button type="button" class="secondary" data-quick-view="all">查看全部候选</button>'}</div>`;
 renderSelection();
}
function personalActions(r){
 return (r.personal_followups||[]).filter(f=>f.favorite||['待联系','已联系','预约看铺'].includes(f.status)).map(f=>`<button type="button" class="link" data-detail="${Number(f.listing_id)}">${f.favorite?'已收藏 · ':''}${esc(f.status)}${f.listing_id!==r.id?' · 出处 #'+Number(f.listing_id):''}</button>`).join('');
}
$('export-listings').onclick=async()=>{
 const generation=sessionGeneration,button=$('export-listings');button.disabled=true;
 try{
  const response=await fetch('/api/v1/exports/listings.csv',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(appliedQuery)});
  if(generation!==sessionGeneration)return;
  if(!response.ok){if(response.status===401){clearWorkspace();$('workspace').hidden=true;$('login').hidden=false;}throw new Error('导出失败，请确认登录状态和筛选条件');}
  const blob=await response.blob();if(generation!==sessionGeneration)return;
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='leaseradar-filtered.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  toast('已导出当前已应用条件的全部结果，包含跨页候选');
 }catch(e){if(generation===sessionGeneration)toast(e.message);}finally{button.disabled=false;}
};
async function loadSources(){
 if(user.role==='admin'){const alerts=await api('/source-alerts');$('source-alerts').innerHTML=alerts.length?`<article class="stack-item"><span class="badge warn">${alerts.length} 个来源异常</span><p>异常来源需核验；受阻或重试耗尽的任务可能已暂停。</p>${alerts.map(a=>`<p class="error">${esc(a.source_id)}：${esc(a.error)}</p>`).join('')}</article>`:'';}else{$('source-alerts').innerHTML='';}

 const rows=await api('/sources');const successes=rows.filter(s=>s.last_success_at);$('stat-sources').textContent=successes.length;
 $('coverage-label').textContent=successes.length?`${successes.length} 个来源有扫描记录`:'来源尚未完成同步';
 $('sources').innerHTML=rows.map(s=>`<article class="stack-item"><span class="badge ${s.status==='healthy'?'':'warn'}">${esc(sourceStates[s.status]||s.status)}</span><h3>${esc(s.name)}</h3><p class="muted">最近成功：${esc(date(s.last_success_at))} · ${esc(s.coverage||'覆盖未验证')}</p>${s.detail_last_success_at?`<p class="muted">最近详情复查：${esc(date(s.detail_last_success_at))} · 核验 ${esc(s.detail_checked)} 条</p>`:''}${s.job?`<p class="muted">最近任务：${esc(jobKinds[s.job.kind]||s.job.kind)} · ${esc(jobStates[s.job.state]||s.job.state)} · 已尝试${esc(s.job.attempts)}次${s.job.retry_at?' · 重试时间：'+esc(date(s.job.retry_at)):''}</p>`:''}${s.error?`<p class="error">${esc(s.error)}</p>`:''}<p class="muted">今日实际扫描 ${esc(s.metrics.pages_today)} / ${esc(s.metrics.known_total_pages??'未知')} 页 · 今日回扫 ${esc(s.metrics.backfill_pages_today)} 页 · 剩余预算 ${esc(s.metrics.remaining_budget)} 页。${esc(s.metrics.warning)}</p><p class="muted">持续监测：${s.enabled?'启用':'关闭'} · ${s.id==='wzcqpt'?'适配器待实现':s.id==='nongjy'?'已核验部分HTML及DOCX字段，其他附件待补强':'已核验栏目，链接型公告关键字段待补齐'}</p>${user.role==='admin'&&s.id!=='wzcqpt'?`<div class="actions"><button class="secondary" data-source-run="${esc(s.id)}">同步一次</button><button class="secondary" data-source-backfill="${esc(s.id)}">续扫一页</button><button class="secondary" data-source-details="${esc(s.id)}">复查活跃详情</button><button class="secondary" data-coverage="${esc(s.id)}">设置回扫预算</button><button class="link" data-source-toggle="${esc(s.id)}" data-enabled="${s.enabled}">${s.enabled?'暂停':'启用'}定时监测</button></div>`:''}</article>`).join('');
}
async function loadSubscriptions(){
 const rows=await api('/subscriptions');$('subscriptions').innerHTML=rows.length?rows.map(s=>`<article class="stack-item"><span class="badge">${s.enabled?'启用':'暂停'}</span><h3>${esc(s.name)}</h3><p class="muted">${esc(Object.entries(s.filters).filter(([k,v])=>v!==false&&v!==null).map(([k,v])=>`${labels[k]||k}：${changeValue(k,v)}`).join(' / ')||'所有条件不限')}<br>未知条件：${s.unknown_policy==='exclude'?'排除':'待确认候选'}<br>报名提醒：${s.reminder_hours.length?s.reminder_hours.map(h=>`提前 ${h} 小时`).join(' / '):'关闭'}</p><div class="actions"><button class="secondary" data-sub-edit="${s.id}">编辑设置</button><button class="secondary" data-sub-toggle="${s.id}">${s.enabled?'暂停':'恢复'}</button><button class="link" data-sub-search="${s.id}">查看匹配候选</button></div></article>`).join(''):'<div class="empty">还没有订阅。选择筛选条件后点击“保存为订阅”。</div>';
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
 const noticeData=await api('/notifications/history?page='+noticePage);const rows=noticeData.items;setPager('notice',noticePage,noticeData.total);
 const [receiptData,health]=await Promise.all([api('/email-deliveries/history?page='+emailPage),api('/health/ready')]);
 const receipts=receiptData.items;setPager('email',emailPage,receiptData.total);await loadDigests();
 $('stat-email').textContent={configured:'已配置',disabled:'未配置',invalid_configuration:'配置错误'}[health.external_notifications]||'待核验';
 const deliveryStates={queued:'等待发送',sending:'正在发送',retry_wait:'等待重试',accepted:'邮件服务器已接受',dead_letter:'发送失败，待处理',ambiguous:'结果不明，待人工核验',cancelled:'已取消',closed:'管理员已关闭'};
 $('email-deliveries').innerHTML=receipts.length?receipts.map(r=>`<article class="stack-item"><span class="badge">${esc(deliveryStates[r.state]||r.state)}</span><p>通知 #${esc(r.notice_id)} · 尝试 ${esc(r.attempts)} 次${r.retry_at?' · 下次重试：'+esc(date(r.retry_at)):''}</p><p class="muted">Message-ID：${esc(r.message_id||'旧记录未保存，请核验服务商原日志')}</p>${r.error?`<p class="muted">${esc(r.error)}</p>`:''}${user.role==='admin'&&['dead_letter','ambiguous'].includes(r.state)?`<button class="secondary" data-delivery-review="${r.id}" data-delivery-state="${r.state}" data-delivery-kind="email">审核发送结果</button>`:''}</article>`).join(''):'<p class="muted">暂无邮件发送记录；未配置时仅使用站内收件箱。</p>';$('stat-notices').textContent=noticeData.unread;
 $('notifications').innerHTML=rows.length?rows.map(r=>`<article class="stack-item"><span class="badge ${r.state==='cancelled'||r.match?.verdict!=='pass'?'warn':''}">${r.state==='cancelled'?'提醒已作废':r.notice_class==='status_update'?'原候选变化':r.match?.verdict!=='pass'?'条件待确认':r.notice_class==='deadline_reminder'?'报名提醒':'明确匹配'} · ${r.read?'已读':'未读'}</span><h3>${esc(r.title||'历史通知：详情待补齐')}</h3><p class="muted">${esc(date(r.created_at))} · ${esc(noticeKinds[r.kind]||r.kind)} · ${esc({queued:'等待处理',accepted:'已入站内收件箱',cancelled:'已作废'}[r.state]||r.state)}</p>${r.kind==='registration_reminder'?`<p>已进入提前 ${esc(r.lead_hours)} 小时提醒窗口。报名截止：${esc(date(r.registration_deadline))}</p><p class="muted">最近核验：${esc(date(r.last_checked_at))}</p>`:''}${(r.changes||[]).length?`<p class="muted">${r.changes.map(c=>`${esc(labels[c.field]||c.field)}：${esc(changeValue(c.field,c.before))} → ${esc(changeValue(c.field,c.after))}`).join('<br>')}</p>`:''}<div class="actions"><button class="secondary" data-detail="${r.listing_id}">查看详情</button><button class="link" data-read="${r.id}">标记已读</button></div></article>`).join(''):'<div class="empty">暂无提醒。保存订阅后，后续采集变化和报名截止提醒会出现在这里。</div>';
}

function showWorkspaceDialog(drawer=false){
 const dialog=$('detail');dialog.classList.toggle('detail-drawer',drawer);
 if(!dialog.open)dialog.showModal();
 dialog.scrollTop=0;
}
async function showDetail(id){
 const r=await api('/listings/'+id);activeDetail=r;$('detail-context').textContent='铺位资料与字段依据';$('detail').setAttribute('aria-label','铺位资料与字段依据');
 const pairs=[['地址',r.address||'待核实'],['面积',`${money(r.area_m2)} ㎡`],['原始价格',`${money(r.raw_amount)} 元 · ${kinds[r.price_kind]||'价格性质待确认'}`],['月租基准',r.first_year_monthly==null?'待确认':`${money(r.first_year_monthly)} 元/月`],['单位面积月租',r.unit_monthly==null?'待确认':`${money(r.unit_monthly)} 元/㎡/月`],['报名截止',date(r.registration_deadline)],['竞价截止',date(r.auction_deadline)],['保证金',r.deposit==null?'待确认':`${money(r.deposit)} 元`],['最后核验',date(r.last_checked_at)]];
 $('detail-body').innerHTML=`${selected.size>=2?'<button class="secondary" data-compare-back="true">返回已选比较</button>':''}<span class="badge">${esc(registrationText(r))}</span><h2>${esc(r.title)}</h2><p class="muted">来源记录 #${r.id} · <a href="${esc(r.source_url)}" target="_blank" rel="noopener noreferrer">打开原始公告 ↗</a></p><button type="button" class="detail-jump" data-evidence-jump="true">跳到关键字段依据 ↓</button><div class="detail-grid">${pairs.map(([k,v])=>`<div><small>${esc(k)}</small>${esc(v)}</div>`).join('')}</div>${r.formula?`<p class="muted">换算：${esc(r.formula)}；税费等成本未完整核实。</p>`:''}<div class="warning">${(r.warnings||[]).map(esc).join('<br>')}</div>${r.source_variants?.length>1?`<h3>多来源原始观察</h3><p class="warning">字段冲突：${r.source_conflicts.map(k=>esc(labels[k]||k)).join(' / ')||'没有已知值冲突'}；各来源字段并列保留，检索时冲突按待确认处理。</p>${r.source_variants.map(v=>`<details><summary>挂牌 #${v.id} · ${esc(v.source_id)}</summary><p>${esc(v.title)}</p><p>${Object.entries(v).filter(([k])=>labels[k]&&k!=='title').map(([k,value])=>`${esc(labels[k])}：${esc(changeValue(k,value))}`).join('<br>')}</p><button class="link" data-detail="${v.id}">查看此来源依据</button></details>`).join('')}`:''}<h3 id="detail-evidence">关键字段依据</h3>${r.evidence.map(e=>`<div class="evidence"><strong>${esc(labels[e.field]||e.field)}</strong>${esc(e.quote)}</div>`).join('')}${user.role==='admin'?reviewForms(r):''}<div id="listing-relations"></div><h3>跟进记录</h3><form id="followup-form" class="followup-form"><select name="status">${['未查看','已查看','待联系','已联系','预约看铺','放弃','已成交'].map(s=>`<option ${r.followup?.status===s?'selected':''}>${s}</option>`).join('')}</select><label class="check"><input name="favorite" type="checkbox" ${r.followup?.favorite?'checked':''}>收藏该铺位</label><textarea name="note" rows="3" maxlength="3000" placeholder="联系情况、看铺记录或放弃原因">${esc(r.followup?.note||'')}</textarea><button class="primary">保存跟进</button></form><h3>版本历史 · ${r.versions.length}</h3><p class="muted">${r.versions.map(v=>esc(date(v.created_at))).join(' / ')}</p><details><summary>查看保存的原文文本</summary><p class="source-text">${esc(r.source_text)}</p></details>`;
 showWorkspaceDialog(true);
 await loadRelations(r.id);bindReviewForms(r);
 $('followup-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{await api(`/listings/${r.id}/followup`,{method:'PATCH',body:JSON.stringify({status:f.elements.status.value,note:f.elements.note.value,favorite:f.elements.favorite.checked})});toast('跟进记录已保存');await loadListings();await loadNotices();}catch(e){toast(e.message);}};
}
$('login-form').onsubmit=async e=>{e.preventDefault();try{const data=Object.fromEntries(new FormData(e.target));await api('/auth/login',{method:'POST',body:JSON.stringify(data)});e.target.reset();await boot();}catch(e){$('login-error').textContent=e.message;}};
$('logout').onclick=async()=>{await api('/auth/logout',{method:'POST'});clearWorkspace();await boot();};
$('filter-form').onsubmit=e=>{e.preventDefault();page=1;loadListings(draftQuery()).catch(e=>toast(e.message));};
$('filter-form').oninput=pendingFilters;
$('filter-form').onchange=pendingFilters;
$('filter-form').onreset=()=>setTimeout(()=>{page=1;loadListings(draftQuery()).catch(e=>toast(e.message));},0);
$('prev').onclick=()=>{if(page>1){page--;loadListings().catch(e=>toast(e.message));}};
$('next').onclick=()=>{if(page*24<total){page++;loadListings().catch(e=>toast(e.message));}};
$('refresh-workspace').onclick=async()=>{const button=$('refresh-workspace');button.disabled=true;try{await refresh();toast('界面数据已刷新；未触发源站抓取');}catch(e){toast(e.message);}finally{button.disabled=false;}};
$('close-detail').onclick=()=>$('detail').close();
function openSubscription(subscription=null){
 editingSubscription=subscription;
 subscriptionFilters=subscription?subscription.filters:appliedQuery.filters;
 $('subscription-filter-summary').textContent='订阅条件：'+filterText(subscriptionFilters);
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
 if(b.dataset.view)await showView(b.dataset.view);
 if(b.dataset.quickView){page=1;await loadListings({...appliedQuery,view:b.dataset.quickView});}
 if(b.dataset.evidenceJump)$('detail-evidence')?.scrollIntoView({block:'start',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
 if(b.dataset.deliveryReview)await openDeliveryReview(b.dataset.deliveryReview,b.dataset.deliveryState,b.dataset.deliveryKind);
 if(b.dataset.coverage)await openCoverage(b.dataset.coverage);
 if(b.dataset.compareBack)$('compare-selected').click();
 if(b.dataset.removeSelection){selected.delete(Number(b.dataset.removeSelection));renderSelection();}
 if(b.dataset.detail)await showDetail(b.dataset.detail);
 if(b.dataset.read){await api('/notifications/'+b.dataset.read,{method:'PATCH'});await loadNotices();}
 if(b.dataset.sourceRun){b.disabled=true;await api('/sources/'+b.dataset.sourceRun+'/runs',{method:'POST'});toast('任务已入队，请稍后查看来源健康');b.disabled=false;await loadSources();}
 if(b.dataset.sourceBackfill){await api('/sources/'+b.dataset.sourceBackfill+'/runs?kind=backfill',{method:'POST'});toast('续扫任务已入队');await loadSources();}
 if(b.dataset.sourceDetails){await api('/sources/'+b.dataset.sourceDetails+'/runs?kind=details',{method:'POST'});toast('活跃详情复查已入队');await loadSources();}
 if(b.dataset.sourceToggle){await api('/sources/'+b.dataset.sourceToggle,{method:'PATCH',body:JSON.stringify({enabled:b.dataset.enabled!=='true'})});await loadSources();}
 if(b.dataset.subSearch){const s=window.currentSubscriptions.find(s=>String(s.id)===b.dataset.subSearch);for(const el of $('filter-form').elements){if(!el.name)continue;if(el.type==='checkbox')el.checked=Boolean(s.filters[el.name]);else el.value=s.filters[el.name]??'';}$('include-unknown').checked=s.unknown_policy!=='exclude';$('sort').value='newest';page=1;document.querySelector('nav [data-view="listings"]').click();await loadListings({...draftQuery(),view:'all'});}
 if(b.dataset.subEdit)openSubscription(window.currentSubscriptions.find(s=>String(s.id)===b.dataset.subEdit));
 if(b.dataset.subToggle){const s=window.currentSubscriptions.find(s=>String(s.id)===b.dataset.subToggle);await api('/subscriptions/'+s.id,{method:'PATCH',body:JSON.stringify({...s,enabled:!s.enabled})});await loadSubscriptions();await loadNotices();}
 }catch(e){b.disabled=false;toast(e.message);}
});
boot();

document.addEventListener('change', e=>{
 if(!e.target.dataset.select)return;
 const id=Number(e.target.dataset.select);
 if(e.target.checked){if(selected.size>=5){e.target.checked=false;toast('最多比较5条');return;}selected.add(id);}else selected.delete(id);
 renderSelection();
});
$('clear-selection').onclick=()=>{selected.clear();renderSelection();};
$('compare-tray-open').onclick=()=>$('compare-selected').click();
$('compare-selected').onclick=async()=>{
 if(selected.size<2){toast('请勾选2–5条候选');return false;}
 try{
  $('detail-context').textContent='候选比较 / COMPARISON';$('detail').setAttribute('aria-label','候选比较');
  const result=await api('/comparisons',{method:'POST',body:JSON.stringify({listing_ids:[...selected]})});
  const rank={starting_bid:0,asking:1,sale:2};
  result.items.sort((a,b)=>(rank[a.price_kind]??3)-(rank[b.price_kind]??3));
  const fields=[['area_m2','面积 · ㎡'],['first_year_monthly','月租基准 · 元'],['unit_monthly','元/㎡/月'],['registration_deadline','报名截止'],['status','报名状态'],['address','地址'],['price_kind','价格性质'],['raw_amount','原价 · 元'],['period_basis','价格周期'],['formula','换算依据'],['deposit','保证金 · 元'],['property_type','物业类型'],['environment','所在环境'],['operation','经营用途'],['last_checked_at','最近核验'],['followup','我的跟进']];
  const value=(r,key)=>key==='status'?registrationText(r):key==='followup'?r.followup?.status||'未查看':['area_m2','raw_amount','first_year_monthly','unit_monthly','deposit'].includes(key)?money(r[key]):['registration_deadline','last_checked_at'].includes(key)?date(r[key]):changeValue(key,r[key]);
  const groupStart=(r,i)=>i>0&&r.price_kind!==result.items[i-1].price_kind?' group-start':'';
  const differences=fields.filter(([key])=>new Set(result.items.map(r=>value(r,key))).size>1).length;
  $('detail-body').innerHTML=`<h2>候选比较 · ${result.items.length} 条</h2><p class="muted">${differences} 项不同；差异行已标记。手机可左右滑动表格，字段列固定。</p><p class="warning">价格性质按列分组，只比较已核实的月租基准。保证金另列，税费等未完整核实；经营用途未知需核验。</p><div class="comparison-scroll" tabindex="0" role="region" aria-label="候选比较表"><table class="comparison"><thead><tr><th scope="col">比较字段</th>${result.items.map((r,i)=>`<th scope="col" class="${groupStart(r,i)}"><span class="badge">${esc(kinds[r.price_kind]||'价格性质待确认')}</span><h3 title="${esc(r.title)}">${esc(r.title)}</h3><button class="link" data-detail="${r.id}">查看原文依据</button></th>`).join('')}</tr></thead><tbody>${fields.map(([key,label])=>{const different=new Set(result.items.map(r=>value(r,key))).size>1;return `<tr class="${different?'different':''}"><th scope="row">${esc(label)}${different?'<small>有差异</small>':''}</th>${result.items.map((r,i)=>`<td class="${r[key]==null&&key!=='followup'?'cell-unknown':''}${groupStart(r,i)}">${esc(value(r,key))}</td>`).join('')}</tr>`;}).join('')}</tbody></table></div>`;
  showWorkspaceDialog();
  return true;
 }catch(e){toast(e.message);return false;}
};

function setPager(prefix,current,count){$(prefix+'-page').textContent=`${current} / ${Math.max(1,Math.ceil(count/20))} · ${count} 条` ;$(prefix+'-prev').disabled=current<=1;$(prefix+'-next').disabled=current*20>=count;}
for(const [prefix,change,load] of [['notice',n=>noticePage+=n,loadNotices],['email',n=>emailPage+=n,loadNotices],['digest',n=>digestPage+=n,loadDigests],['review',n=>reviewPage+=n,loadReview],['incident',n=>incidentPage+=n,loadIncidents]])for(const [suffix,n] of [['prev',-1],['next',1]])$(prefix+'-'+suffix).onclick=()=>{change(n);load().catch(e=>toast(e.message));};
async function loadPreferences(){const data=await api('/notification-preferences');const f=$('preference-form');for(const key of ['mode','timezone','digest_time','quiet_start','quiet_end'])f.elements[key].value=data[key]??'';f.elements.urgent_override.checked=data.urgent_override;}
$('preference-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{const body=Object.fromEntries(new FormData(f));body.urgent_override=f.elements.urgent_override.checked;body.quiet_start=body.quiet_start||null;body.quiet_end=body.quiet_end||null;const r=await api('/notification-preferences',{method:'PUT',body:JSON.stringify(body)});toast(r.message);}catch(e){toast(e.message);}};
async function loadDigests(){const d=await api('/digests?page='+digestPage);setPager('digest',digestPage,d.total);$('digests').innerHTML=d.items.length?d.items.map(r=>`<article class="stack-item"><span class="badge">摘要 #${r.id}</span><p>${esc(date(r.window_start))} 至 ${esc(date(r.window_end))} · ${r.notice_ids.length} 条事件</p><p class="muted">${r.sources.map(s=>`${esc(s.id)}：${esc(sourceStates[s.status]||s.status)}，${s.enabled?'监测启用':'监测暂停'}；${esc(s.coverage||'覆盖未知')}`).join('<br>')}</p>${r.items.map(n=>`<p>${n.state==='cancelled'?'已作废：':''}${esc(n.title||'历史通知')} <button class="link" data-detail="${n.listing_id}">查看候选</button></p>`).join('')}<p class="muted">原始通知编号：${r.notice_ids.map(esc).join(' / ')}；作废项以提醒历史当前状态为准。</p></article>`).join(''):'<p class="muted">暂无摘要。保存通知节奏后，worker在所选时间汇总待确认或每日通知。</p>';}
async function loadIncidents(){const d=await api('/source-incidents?page='+incidentPage);setPager('incident',incidentPage,d.total);$('incidents').innerHTML=d.items.map(r=>`<article class="stack-item"><span class="badge ${r.state==='open'?'warn':''}">${r.state==='open'?'待处理':'已结束，现状须核验'}</span><h3>${esc(r.source_id)}</h3><p>${esc(r.message)}</p><p class="muted">开始 ${esc(date(r.opened_at))} · 结束 ${esc(date(r.resolved_at))}</p></article>`).join('')||'<p class="muted">暂无告警历史。监测暂停不会冒充持续成功。</p>';}
function reviewForms(r){return `<details class="workflow-panel"><summary>人工纠正与关联（管理员）</summary><p class="muted">依据由你核验，系统不替你联系出租方。未知可留空，禁止据未禁止推断允许。</p><form id="correction-form" class="workflow-grid"><label>纠正字段<select name="field">${['address','city','district','area_m2','raw_amount','price_kind','period_basis','registration_deadline','auction_deadline','operation','property_type','environment','status','deposit'].map(k=>`<option value="${k}">${esc(labels[k]||k)}</option>`).join('')}</select></label><label id="correction-value-label">核验值<input name="value" maxlength="2000" placeholder="留空表示未知"></label><label class="wide">依据 / 联系核验记录<textarea name="quote" minlength="5" maxlength="3000" required></textarea></label><label class="wide">纠正原因<textarea name="reason" minlength="5" maxlength="1000" required></textarea></label><p id="correction-value-help" class="muted wide">选择字段后填写已核验值；日期按北京时间保存。留空表示未知。</p><button class="primary">保存有依据的纠正</button></form><h3>关联另一条挂牌</h3><form id="relation-form" class="workflow-grid"><label>另一挂牌编号<input name="right_id" type="number" min="1" required></label><label>关系<select name="kind"><option value="same_round">同一挂牌的不同出处</option><option value="relisting">同一资产重新挂牌</option><option value="same_asset">同一资产不同机会</option><option value="bundle_member">整体与成员关系</option></select></label><label class="wide">关联依据<textarea name="reason" minlength="5" maxlength="1000" required></textarea></label><p class="muted wide">仅建立可撤销关联，不拆整体价格、不覆盖各来源字段和私人跟进。已有相同挂牌不再作为独立新增机会提醒。</p><button class="secondary">保存人工关联</button></form></details>`;}
function bindReviewForms(r){if(user.role!=='admin')return;$('correction-form').elements.field.onchange=()=>correctionValueField(r);correctionValueField(r);$('correction-form').onsubmit=async e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));if(body.field.endsWith('_deadline')&&body.value)body.value+=body.value.length===16?':00+08:00':'+08:00';try{await api('/corrections',{method:'POST',body:JSON.stringify({...body,value:body.value||null,listing_id:r.id,base_version_id:r.version_id})});toast('纠正已保存，来源核验时间未改变');await showDetail(r.id);await loadReview();await loadListings();}catch(e){toast(e.message);}};$('relation-form').onsubmit=async e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));try{await api('/listing-relations',{method:'POST',body:JSON.stringify({...body,left_id:r.id,right_id:Number(body.right_id)})});toast('关联已保存');await loadRelations(r.id);}catch(e){toast(e.message);}};}
const relationKinds={same_round:'同一挂牌不同出处',relisting:'重新挂牌',same_asset:'同一资产',bundle_member:'整体与成员'};
async function loadRelations(id){const rows=await api('/listing-relations/'+id);$('listing-relations').innerHTML='<h3>关联与重新挂牌时间线</h3>'+ (rows.length?rows.map(r=>`<article class="evidence"><strong>${esc(relationKinds[r.kind])} · ${r.state==='active'?'有效':'已撤销'}</strong><p>挂牌 #${r.left_id} ↔ #${r.right_id} · ${esc(date(r.created_at))}</p><p>${esc(r.reason)}</p><button class="link" data-detail="${r.left_id===Number(id)?r.right_id:r.left_id}">查看另一挂牌依据</button>${user.role==='admin'&&r.state==='active'?`<form data-revert-relation="${r.id}"><label>撤销原因<input name="reason" minlength="5" maxlength="1000" required></label><button class="secondary">撤销关联</button></form>`:''}</article>`).join(''):'<p class="muted">尚无人工确认关联；系统不会仅按相似地址自动合并。</p>');document.querySelectorAll('[data-revert-relation]').forEach(f=>f.onsubmit=async e=>{e.preventDefault();try{await api('/listing-relations/'+f.dataset.revertRelation+'/revert',{method:'POST',body:JSON.stringify({reason:f.elements.reason.value})});await loadRelations(id);toast('关联已撤销，历史保留');}catch(e){toast(e.message);}});}
async function loadReview(){const d=await api('/review-queue?page='+reviewPage);setPager('review',reviewPage,Math.max(d.total,d.source_conflict_total));$('review-page').textContent=`第 ${reviewPage} 页 · 纠正 ${d.total} 条 / 来源冲突 ${d.source_conflict_total} 组`;const conflictHtml=d.source_conflicts.map(r=>`<article class="stack-item"><span class="badge warn">多来源冲突待核验</span><h3>${esc(r.title)}</h3><p>${r.source_conflicts.map(k=>esc(labels[k]||k)).join(' / ')}</p>${r.source_variants.map(v=>`<p>挂牌 #${v.id}：${r.source_conflicts.map(k=>`${esc(labels[k]||k)} ${esc(changeValue(k,v[k]))}`).join(' · ')} <button class="link" data-detail="${v.id}">核验该出处</button></p>`).join('')}</article>`).join('');$('review-queue').innerHTML=d.items.length?d.items.map(r=>`<article class="stack-item"><span class="badge ${r.state==='conflict'?'warn':''}">${{active:'纠正有效',conflict:'来源冲突待审',reverted:'已撤销'}[r.state]}</span><h3>挂牌 #${r.listing_id} · ${esc(labels[r.field]||r.field)}</h3><p>原值 ${esc(changeValue(r.field,r.original))} → 人工值 ${esc(changeValue(r.field,r.value))}<br>最新源观测 ${esc(changeValue(r.field,r.source_value))}</p><p class="muted">${esc(r.quote)}；${esc(r.reason)}</p><button class="link" data-detail="${r.listing_id}">查看公告依据</button>${r.state!=='reverted'?`<form data-resolve-correction="${r.id}" data-version="${r.expected_version_id}"><label>处理依据<input name="reason" minlength="5" maxlength="1000" required></label><select name="action"><option value="revert">撤销并恢复最新源值</option><option value="keep">核验后继续保留人工值</option></select><button class="secondary">保存审核结果</button></form>`:''}</article>`).join(''):'<div class="empty">暂无人工纠正。可从公告详情创建有依据的纠正。</div>';$('review-queue').insertAdjacentHTML('afterbegin',conflictHtml);document.querySelectorAll('[data-resolve-correction]').forEach(f=>f.onsubmit=async e=>{e.preventDefault();try{await api('/corrections/'+f.dataset.resolveCorrection+'/resolve',{method:'POST',body:JSON.stringify({action:f.elements.action.value,reason:f.elements.reason.value,expected_version_id:Number(f.dataset.version)})});await loadReview();await loadListings();toast('审核已保存');}catch(e){toast(e.message);}});}
async function openCoverage(id){const rows=await api('/sources');const s=rows.find(r=>r.id===id);$('detail-context').textContent='来源回扫设置';$('detail-body').innerHTML=`<h2>${esc(s.name)} · 回扫预算</h2><p class="muted">只修改预算，不会自动启用来源。每日预算按上海日历计算，前台首页与详情复查优先；动态页码不构成全量一致快照。</p><form id="coverage-form"><label>每日回扫页数上限<input name="daily_page_budget" type="number" min="1" max="240" value="${s.metrics.daily_page_budget}" required></label><label>每批页数<input name="backfill_batch_pages" type="number" min="1" max="10" value="${s.metrics.backfill_batch_pages}" required></label><button class="primary">保存回扫预算</button></form>`;showWorkspaceDialog();$('coverage-form').onsubmit=async e=>{e.preventDefault();try{const f=e.target;await api('/sources/'+id+'/coverage-policy',{method:'PUT',body:JSON.stringify({daily_page_budget:Number(f.elements.daily_page_budget.value),backfill_batch_pages:Number(f.elements.backfill_batch_pages.value)})});$('detail').close();await loadSources();toast('预算已保存，持续监测状态未改变');}catch(e){toast(e.message);}};}

$('import-form').onsubmit=async e=>{e.preventDefault();try{const r=await api('/imports',{method:'POST',body:JSON.stringify({url:e.target.elements.url.value})});toast(`任务 #${r.job_id}：${r.message}`);await loadSources();}catch(e){toast(e.message);}};

function correctionValueField(r){
 const field=$('correction-form').elements.field.value;
 const options={price_kind:['starting_bid','asking','sale'],period_basis:['first_year','monthly'],status:['open','closed','withdrawn','sold','failed','unknown'],operation:['coffee_beverage','restaurant','retail'],property_type:['shop','commercial_unit','office','warehouse','apartment'],environment:['campus','apartment_building','street','market']};
 const dateField=field.endsWith('_deadline');
 $('correction-value-label').innerHTML=`核验值${dateField?' · 北京时间':''}`+(options[field]?`<select name="value"><option value="">未知 / 清空</option>${options[field].map(v=>`<option value="${v}" ${r[field]===v?'selected':''}>${esc(changeValue(field,v))}</option>`).join('')}</select>`:`<input name="value" ${dateField?'type="datetime-local"':['area_m2','raw_amount','deposit'].includes(field)?'type="number" min="0" step="0.0001"':''} maxlength="2000" placeholder="留空表示未知" value="${esc(dateField?'':r[field]??'')}">`);
}

let documentPage=1;
$('lease-form').onsubmit=async e=>{
 e.preventDefault();const f=e.target;
 try{
  const values=Object.fromEntries(new FormData(f));if(values.basis!=='segments'&&!values.amount)throw new Error('请填写所选口径的金额');if(values.basis==='segments'&&!values.segments.trim())throw new Error('请填写完整的分段月租及依据');const body={basis:values.basis,term_months:Number(values.term_months)};
  for(const key of ['amount','annual_escalation_percent','nonrefundable_fees','refundable_deposit'])body[key]=values[key]||null;
  for(const key of ['annual_compound','fixed_rent','prorate_partial_year','amount_before_free'])body[key]=f.elements[key].checked;
  body.free_months=values.free_months.trim()?values.free_months.replace(/，/g,',').split(',').map(x=>Number(x.trim())):[];
  body.segments=values.segments.trim()?values.segments.split('\n').filter(x=>x.trim()).map(line=>{const [start,end,monthly,...quote]=line.replace(/，/g,',').split(',');return {start_month:Number(start),end_month:Number(end),monthly:monthly?.trim(),quote:quote.join(',').trim()};}):[];
  body.evidence=Object.fromEntries(['basis','term_months','amount','escalation','free_months','fees','deposit','proration','fixed_rent','amount_before_free'].map(key=>[key,values.quote]));
  const r=await api('/lease-calculations',{method:'POST',body:JSON.stringify(body)});
  $('lease-result').innerHTML=`<article class="stack-item"><h3>已核验条款计算结果</h3><div class="detail-grid">${[['首年平均月租（含已知免租）',r.first_year_monthly],['租期平均月租',r.average_monthly],['已知租金总额',r.total_rent],['已核验不可退费用',r.nonrefundable_fees],['可退保证金现金占用',r.refundable_deposit]].map(([key,value])=>`<div><small>${esc(key)}</small>${money(value)} 元</div>`).join('')}</div><p class="warning">${r.warnings.map(esc).join('<br>')}</p>${r.formula?`<p>${esc(r.formula)}</p>`:''}<details><summary>查看计算月度明细及依据</summary><p>${esc(values.quote)}</p>${r.schedule.map(m=>`<p>第${m.month}月：${money(m.rent)} 元</p>`).join('')}</details></article>`;
 }catch(e){$('lease-result').innerHTML='';toast(e.message);}
};
$('document-form').onsubmit=async e=>{e.preventDefault();try{const generation=sessionGeneration;const f=e.target;const file=f.elements.file.files[0];if(!file||file.size>5000000)throw new Error('请选择不超过5MB的PDF或DOCX');const bytes=new Uint8Array(await file.arrayBuffer());if(generation!==sessionGeneration||!user)throw new Error('会话已变化，附件未提交');let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));const r=await api('/document-reviews',{method:'POST',body:JSON.stringify({filename:file.name,content_base64:btoa(binary),listing_id:f.elements.listing_id.value?Number(f.elements.listing_id.value):null})});f.reset();toast(r.message);await loadDocuments();}catch(e){toast(e.message);}};
async function loadDocuments(){const [d,downloads]=await Promise.all([api('/document-reviews?page='+documentPage),api('/document-downloads?page='+documentPage)]);setPager('document',documentPage,Math.max(d.total,downloads.total));$('document-reviews').innerHTML=`<p class="muted">${esc(d.worker_note)}</p><h3>来源附件下载 · ${{configured:'已配置',disabled:'关闭',invalid_configuration:'配置待核验'}[downloads.configuration]}</h3><p class="muted">下载记录 ${downloads.total} 条；获取成功仅表示进入审核，不代表字段已核实。</p>`+downloads.items.map(r=>`<article class="stack-item"><span class="badge">${{queued:'等待下载',retry_wait:'等待有限重试',downloading:'正在获取',downloaded:'已保存并关联审核',blocked:'访问受阻，未绕过',failed:'获取失败，保留记录',cancelled:'版本或归属变化，已停止'}[r.state]||esc(r.state)}</span><p>下载 #${r.id} · 来源版本 #${r.version_id} · 尝试 ${r.attempts} 次</p><p class="muted">${esc(r.url)}</p>${r.error?`<p class="warning">${esc(r.error)}</p>`:''}${r.retry_at?`<p>下次尝试 ${esc(date(r.retry_at))}</p>`:''}${r.review_id?`<p>已关联私有审核 #${r.review_id}</p>`:''}</article>`).join('')+'<h3>私有附件审核</h3>'+d.items.map(r=>`<article class="stack-item"><span class="badge">${{queued:'等待提取worker',review:'提取完成，待人工核验',failed:'提取失败，保留待复核'}[r.state]}</span><h3>${esc(r.filename)}</h3><p class="muted">附件 #${r.id} · ${r.listing_id?'挂牌 #'+r.listing_id:'未关联挂牌'} · SHA256 ${esc(r.sha256)}</p>${r.origin_url?`<p class="muted">采集附件 · 来源版本 #${esc(r.origin_version_id)}<br>${esc(r.origin_url)}</p>`:''}${r.error?`<p class="warning">${esc(r.error)}</p>`:''}${r.pages.map(p=>`<details><summary>${esc(p.position)} · ${p.method==='ocr_review'?'OCR待人工复核':'提取文字'}</summary><p class="source-text">${esc(p.text)}</p></details>`).join('')}${r.listing_id?`<button class="link" data-detail="${r.listing_id}">核验后在挂牌详情创建有依据的纠正</button>`:''}</article>`).join('');}
$('refresh-documents').onclick=()=>loadDocuments().catch(e=>toast(e.message));
$('document-prev').onclick=()=>{documentPage--;loadDocuments().catch(e=>toast(e.message));};$('document-next').onclick=()=>{documentPage++;loadDocuments().catch(e=>toast(e.message));};

async function openDeliveryReview(id,state,kind){
 $('detail-context').textContent='发送结果审核';$('detail').setAttribute('aria-label','发送结果审核');
 const choices=state==='ambiguous'?[['confirm_accepted','回执确认服务商已接受'],['confirm_unsent','回执确认未接受，重试一次'],['close','关闭，不再发送']]:[['retry','修复后重试一次'],['close','关闭，不再发送']];
 $('detail-body').innerHTML=`<h2>发送记录 #${esc(id)} · ${state==='ambiguous'?'结果不明':'发送失败'}</h2><p class="warning">结果不明须核验原Message-ID和服务商日志。没有回执依据不能重发；已接受不代表最终邮箱投递。重试保留原接收目标与累计次数，最多再尝试一次。</p><form id="delivery-review-form"><label>处理方式<select name="action">${choices.map(([value,label])=>`<option value="${value}">${label}</option>`).join('')}</select></label><label>审核原因<textarea name="reason" required minlength="5" maxlength="1000"></textarea></label><label>服务商回执 / 日志核验依据<textarea name="receipt" maxlength="2000" placeholder="确认结果不明时必填；请保留服务商记录号及核验结论"></textarea></label><label>服务商接受时间 · 北京时间<input name="accepted_at" type="datetime-local"></label><button class="primary">保存审核结果</button></form>`;
 showWorkspaceDialog();
 $('delivery-review-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{const body=Object.fromEntries(new FormData(f));body.expected_state=state;body.accepted_at=body.accepted_at?body.accepted_at+':00+08:00':null;const r=await api((kind==='incident'?'/incident-emails/':'/email-deliveries/')+id+'/review',{method:'POST',body:JSON.stringify(body)});$('detail').close();toast(r.message);await loadNotices();await loadIncidentEmails();}catch(e){toast(e.message);}};
}
async function loadIncidentEmails(){
 const [d,readiness]=await Promise.all([api('/incident-emails?page='+incidentEmailPage),api('/setup-readiness')]);
 setPager('incident-email',incidentEmailPage,d.total);
 $('incident-email-status').textContent={configured:'来源告警邮件已配置',disabled:'来源告警邮件关闭；最后统一配置即可',invalid_configuration:'告警邮件配置需核验管理员及通道'}[readiness.source_alert_email];
 const stateLabels={queued:'待发送',sending:'发送中',accepted:'服务商已接受',retry_wait:'等待重试',dead_letter:'发送失败',ambiguous:'结果不明',cancelled:'条件失效已取消',closed:'管理员已关闭'};
 $('incident-emails').innerHTML=d.items.length?d.items.map(r=>`<article class="stack-item"><span class="badge">${esc(stateLabels[r.state]||r.state)}</span><h3>异常 #${r.incident_id} · ${r.phase==='open'?'异常开始':'异常结束，现状须核验'}</h3><p>发送记录 #${r.id} · 累计尝试 ${r.attempts} 次</p><p class="muted">Message-ID：${esc(r.message_id||'尚未记录')}</p>${r.error?`<p class="muted">${esc(r.error)}</p>`:''}${['dead_letter','ambiguous'].includes(r.state)?`<button class="secondary" data-delivery-review="${r.id}" data-delivery-state="${r.state}" data-delivery-kind="incident">审核告警发送结果</button>`:''}</article>`).join(''):'<p class="muted">暂无来源告警邮件记录。站内异常与恢复历史仍可查看。</p>';
}
$('incident-email-prev').onclick=()=>{incidentEmailPage--;loadIncidentEmails().catch(e=>toast(e.message));};$('incident-email-next').onclick=()=>{incidentEmailPage++;loadIncidentEmails().catch(e=>toast(e.message));};


async function showView(view){
 const b=document.querySelector('nav [data-view="'+view+'"]');
 if(!b)throw new Error('页面不存在');
 document.querySelectorAll('nav button').forEach(n=>n.classList.toggle('active',n===b));
 for(const v of ['listings','subscriptions','notifications','sources','review','tools'])$('view-'+v).hidden=v!==view;
 $('page-title').textContent=b.textContent.trim();renderSelection();await refresh();
}
const demoSteps=[
 ['自由筛选','应用面积≥30㎡、月租≤12000、仅可报名并包含待确认；显示明确匹配与未知的差别。'],
 ['比较三条候选','比较年租A/B与周期未知记录；价格性质分别分组，未知周期不换算。关闭弹窗后继续。'],
 ['查看金额依据','打开A的字段依据与月租公式；经营许可和完整成本仍待核验。关闭弹窗后继续。'],
 ['查看周期未知','标题含五年不代表金额为五年总租金；不能直接除以60。关闭弹窗后继续。'],
 ['提醒收件箱','查看合成96000→90000的同口径变化及待确认提醒；站内入箱不等于外部投递。'],
 ['跟进与笔记','打开合成跟进记录，可自行演示编辑；本路线不会自动保存或伪造真实联系。关闭弹窗后继续。'],
 ['来源与受阻','查看合成访问受阻与覆盖边界；历史数据保留，没有绕过访问控制。']
];
async function loadDemoRoute(){
 $('demo-route').hidden=true;demoScenario=null;
 if(user?.mode!=='demo'||user.role!=='admin')return;
 try{demoScenario=await api('/demo/scenario');$('demo-route').hidden=false;renderDemoRoute();}
 catch(e){if(user&&e.message.includes('过期'))toast(e.message);}
}
function renderDemoRoute(){
 const done=demoRouteIndex>=demoSteps.length-1;
 $('demo-route-title').textContent=demoRouteIndex<0?'7步走完整个流程':demoSteps[demoRouteIndex][0];
 $('demo-route-note').textContent=demoRouteIndex<0?'合成场景：按钮只切换查询与视图，不会重置数据库或发送外部消息。':demoSteps[demoRouteIndex][1];
 $('demo-route-progress').textContent=demoRouteIndex<0?'尚未开始':`第 ${demoRouteIndex+1} / ${demoSteps.length} 步${done?' · 路线已走完，仍是合成演示':''}`;
 $('demo-route-next').disabled=demoRouteBusy||done;
 $('demo-route-reset').disabled=demoRouteBusy;
 $('demo-route-next').textContent=demoRouteIndex<0?'开始演示':done?'路线已走完':'下一步：'+demoSteps[demoRouteIndex+1][0];
}
async function runDemoStep(index){
 if(!demoScenario||demoRouteBusy||index<0||index>=demoSteps.length)return;
 const generation=sessionGeneration;demoRouteBusy=true;renderDemoRoute();
 try{
  if($('detail').open)$('detail').close();
  if(index===0){
   const form=$('filter-form');form.reset();form.elements.area_m2_min.value='30';form.elements.first_year_monthly_max.value='12000';form.elements.registration_open.checked=true;
   $('include-unknown').checked=true;$('sort').value='newest';$('filter-panel').open=true;selected.clear();page=1;appliedQuery={...draftQuery(),view:'all'};await showView('listings');
  }else if(index===1){
   await showView('listings');selected.clear();demoScenario.comparison_ids.forEach(id=>selected.add(id));renderSelection();if(!await $('compare-selected').onclick())throw new Error('比较尚未打开，请重试当前步骤');
  }else if(index===2||index===5){await showView('listings');await showDetail(demoScenario.detail_id);if(index===5)$('followup-form').scrollIntoView({block:'center'});}
  else if(index===3){await showView('listings');await showDetail(demoScenario.unknown_id);}
  else if(index===4){noticePage=1;await showView('notifications');}
  else if(index===6){await showView('sources');}
  if(generation===sessionGeneration)demoRouteIndex=index;
 }catch(e){toast(e.message);}finally{if(generation===sessionGeneration){demoRouteBusy=false;renderDemoRoute();}}
}
$('demo-route-next').onclick=()=>runDemoStep(demoRouteIndex+1);
$('demo-route-reset').onclick=()=>runDemoStep(0);
