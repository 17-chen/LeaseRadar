import hashlib
import secrets
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StrictInt, model_validator
from sqlalchemy import select, text
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from .config import ROOT, DATA, MODE, COOKIE_SECURE, SESSION_COOKIE_NAME
from .db import Session, User, LoginSession, Source, Job, Listing, Evidence, Version, RawDocument, Subscription, Outbox, Followup, CrawlRun
from .service import listing_data
from .domain import match

app = FastAPI(title='LeaseRadar', version='0.1.16')
hasher = PasswordHasher()
login_attempts = {}

@app.middleware('http')
async def cache_policy(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api/v1/') else 'no-cache'
    return response

def database():
    with Session() as db:
        yield db

def current_user(request: Request, db=Depends(database)):
    token = request.cookies.get(SESSION_COOKIE_NAME, '')
    session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
    if not session or datetime.fromisoformat(session.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(401, '请登录')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), session.csrf):
            raise HTTPException(403, 'CSRF校验失败')
    user = db.get(User, session.user_id)
    if not user: raise HTTPException(401, '账号不存在')
    request.state.session = session
    return user

def admin(user=Depends(current_user)):
    if user.role != 'admin': raise HTTPException(403, '需要管理员权限')
    return user

class LoginInput(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)

@app.post('/api/v1/auth/login')
def login(data: LoginInput, request: Request, response: Response, db=Depends(database)):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, '拒绝跨站登录')
    key = request.client.host
    timestamp = datetime.now(timezone.utc).timestamp()
    attempts = [t for t in login_attempts.get(key, []) if timestamp - t < 300]
    if len(attempts) >= 10: raise HTTPException(429, '尝试过多，请5分钟后重试')
    attempts.append(timestamp); login_attempts[key] = attempts
    user = db.scalar(select(User).where(User.username == data.username))
    try:
        valid = user is not None and hasher.verify(user.password_hash, data.password)
    except VerificationError:
        valid = False
    if not valid: raise HTTPException(401, '账号或密码错误')
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(LoginSession(token=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, csrf=csrf,
                        expires_at=(datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()))
    db.commit(); login_attempts.pop(key, None)
    response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, secure=COOKIE_SECURE, samesite='lax', max_age=43200)
    return {'username': user.username, 'role': user.role, 'csrf': csrf}

@app.get('/api/v1/auth/me')
def me(request: Request, user=Depends(current_user)):
    return {'username': user.username, 'role': user.role, 'csrf': request.state.session.csrf, 'mode': MODE}

@app.get('/api/v1/demo/scenario')
def demo_scenario(user=Depends(current_user),db=Depends(database)):
    # An ordinary demo database is not proof that these scenario IDs exist.
    if MODE!='demo':raise HTTPException(404,'真实环境没有演示路线')
    if user.role!='admin':raise HTTPException(403,'演示路线仅向演示管理员开放')
    import json
    marker=DATA/'demo-proof.json'
    try:
        if marker.is_symlink() or marker.stat().st_size>4000:raise ValueError()
        proof=json.loads(marker.read_text())
        if not isinstance(proof,dict) or proof.get('schema')!=1 or proof.get('mode')!='demo' or proof.get('synthetic') is not True or proof.get('owner_user_id')!=user.id:raise ValueError()
        ids=proof.get('comparison_ids')
        if not isinstance(ids,list) or len(ids)!=3 or len(set(ids))!=3 or any(type(x) is not int or x<=0 for x in ids):raise ValueError()
        if proof.get('detail_id')!=ids[0] or proof.get('unknown_id')!=ids[-1]:raise ValueError()
        for identity in ids:
            listing=db.get(Listing,identity);version=db.get(Version,listing.current_version_id) if listing else None
            if not version or not isinstance(version.fields.get('title'),str) or not version.fields['title'].startswith('合成'):raise ValueError()
        from .domain import aware_time
        known=db.get(Version,db.get(Listing,ids[0]).current_version_id)
        cutoff=aware_time(known.fields.get('registration_deadline'))
        if cutoff is None or cutoff<=datetime.now(timezone.utc):raise HTTPException(409,'演示日期已过期，请运行scripts/demo.py新建演示')
        return {'synthetic':True,'comparison_ids':ids,'detail_id':ids[0],'unknown_id':ids[-1]}
    except (OSError,ValueError,TypeError):raise HTTPException(404,'此数据库未配置演示路线；请用scripts/demo.py新建')

@app.post('/api/v1/auth/logout')
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(database)):
    db.delete(db.get(LoginSession, request.state.session.token)); db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, secure=COOKIE_SECURE, samesite='lax')
    return {'ok': True}

class Filters(BaseModel):
    keyword: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=50)
    district: str | None = Field(default=None, max_length=50)
    property_type: str | None = Field(default=None, max_length=40)
    environment: str | None = Field(default=None, max_length=40)
    operation: str | None = Field(default=None, max_length=40)
    status: str | None = Field(default=None, max_length=40)
    price_kind: Literal['starting_bid', 'asking', 'sale'] | None = None
    area_m2_min: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    area_m2_max: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    first_year_monthly_min: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    first_year_monthly_max: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    registration_open: bool = False
    @model_validator(mode='after')
    def bounds(self):
        for field in ['area_m2', 'first_year_monthly']:
            lo, hi = getattr(self, field+'_min'), getattr(self, field+'_max')
            if lo is not None and hi is not None and lo > hi: raise ValueError('下限不能大于上限')
        return self

class SearchInput(BaseModel):
    filters: Filters = Field(default_factory=Filters)
    include_unknown: bool = True
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=24, ge=1, le=100)
    sort: Literal['newest', 'monthly'] = 'newest'
    view: Literal['all', 'recent', 'deadline', 'review', 'favorites', 'following'] = 'all'

def searched_rows(data: SearchInput, user, db):
    rows = []
    from .resolution import grouped_rows
    from .listing_views import in_quick_view
    from datetime import datetime, timezone
    at = datetime.now(timezone.utc)
    for row in grouped_rows(db, user.id):
        result = match(row, data.filters.model_dump(exclude_none=True))
        if result['verdict'] == 'fail' or (not data.include_unknown and result['verdict'] == 'unknown'): continue
        candidate = {**row, 'match': result}
        if in_quick_view(candidate, data.view, at): rows.append(candidate)
    if data.sort == 'monthly':
        # Group price kind; unknown values sort last, never as zero.
        from decimal import Decimal
        rows.sort(key=lambda r: (r.get('price_kind') or 'unknown', r.get('first_year_monthly') is None, Decimal(r['first_year_monthly']) if r.get('first_year_monthly') else Decimal('Infinity')))
    return rows

@app.post('/api/v1/listings/search')
def search(data: SearchInput, user=Depends(current_user), db=Depends(database)):
    rows = searched_rows(data, user, db)
    total = len(rows); offset = (data.page - 1) * data.limit
    return {'items': rows[offset:offset+data.limit], 'total': total, 'page': data.page, 'mode': MODE}

@app.get('/api/v1/listings/{listing_id}')
def detail(listing_id: int, user=Depends(current_user), db=Depends(database)):
    listing = db.get(Listing, listing_id)
    if not listing: raise HTTPException(404, '记录不存在')
    row = listing_data(db, listing, user.id)
    row['evidence'] = [{'field': e.field, 'quote': e.quote} for e in db.scalars(select(Evidence).where(Evidence.version_id == listing.current_version_id))]
    row['versions'] = [{'id': v.id, 'created_at': v.created_at, 'fields': v.fields} for v in db.scalars(select(Version).where(Version.listing_id == listing.id).order_by(Version.id.desc()))]
    row['source_text'] = db.get(RawDocument, db.get(Version, listing.current_version_id).raw_id).text
    from .resolution import grouped_rows
    group = next((g for g in grouped_rows(db, user.id) if listing.id in g['related_listing_ids']), None)
    row['source_variants'] = group['source_variants'] if group else []
    row['source_conflicts'] = group['source_conflicts'] if group else []
    return row

class CompareInput(BaseModel):
    listing_ids: list[int] = Field(min_length=2, max_length=5)

@app.post('/api/v1/comparisons')
def compare(data: CompareInput, user=Depends(current_user), db=Depends(database)):
    if len(set(data.listing_ids)) != len(data.listing_ids): raise HTTPException(422, '不能重复选择同一挂牌')
    rows = []
    from .resolution import grouped_rows
    resolved = grouped_rows(db, user.id)
    for lid in data.listing_ids:
        listing = db.get(Listing, lid)
        if not listing: raise HTTPException(404, '挂牌不存在')
        group = next(g for g in resolved if lid in g['related_listing_ids'])
        if any(r['id'] == group['id'] for r in rows): raise HTTPException(422, '选择包含已关联的同一挂牌，请选择不同机会')
        rows.append(group)
    return {'items': rows, 'warning': '起始价、挂牌价分组比较；保证金不是租金，税费未知时无法得出最低总成本。'}

@app.get('/api/v1/exports/listings.csv')
def export(user=Depends(current_user), db=Depends(database)):
    from .resolution import grouped_rows
    return csv_response(grouped_rows(db, user.id))

@app.post('/api/v1/exports/listings.csv')
def export_filtered(data: SearchInput, user=Depends(current_user), db=Depends(database)):
    # Full applied result set, not just the current page; same semantics as search.
    return csv_response(searched_rows(data, user, db))

def csv_response(rows):
    import csv, io
    buf = io.StringIO(); buf.write('\ufeff')
    writer = csv.writer(buf)
    keys = ['id', 'title', 'address', 'area_m2', 'raw_amount', 'price_kind', 'period_basis', 'first_year_monthly', 'registration_deadline', 'source_url']
    writer.writerow(keys)
    for fields in rows:
        values = []
        for key in keys:
            value = '' if fields.get(key) is None else str(fields[key])
            if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t','\r','\n')): value = "'" + value
            values.append(value)
        writer.writerow(values)
    return Response(buf.getvalue(), media_type='text/csv; charset=utf-8', headers={'Content-Disposition':'attachment; filename="leaseradar.csv"'})

class FollowupInput(BaseModel):
    status: Literal['未查看', '已查看', '待联系', '已联系', '预约看铺', '放弃', '已成交'] = '未查看'
    note: str = Field(default='', max_length=3000)
    favorite: bool = False

@app.patch('/api/v1/listings/{listing_id}/followup')
def followup(listing_id: int, data: FollowupInput, user=Depends(current_user), db=Depends(database)):
    if not db.get(Listing, listing_id): raise HTTPException(404)
    row = db.scalar(select(Followup).where(Followup.user_id == user.id, Followup.listing_id == listing_id))
    if not row: row = Followup(user_id=user.id, listing_id=listing_id); db.add(row)
    for k, v in data.model_dump().items(): setattr(row, k, v)
    from .notifications import cancel_invalid_reminders
    cancel_invalid_reminders(db)
    db.commit(); return {'ok': True}

class SubscriptionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: Filters = Field(default_factory=Filters)
    unknown_policy: Literal['review_digest', 'exclude'] = 'review_digest'
    enabled: bool = True
    reminder_hours: list[StrictInt] = Field(default_factory=lambda: [72, 24], max_length=3)

    @model_validator(mode='after')
    def valid_reminders(self):
        if any(not 1 <= hour <= 168 for hour in self.reminder_hours) or len(set(self.reminder_hours)) != len(self.reminder_hours):
            raise ValueError('报名提醒须为1–168小时，最多3个不重复时间；空列表关闭提醒')
        self.reminder_hours.sort(reverse=True)
        return self

@app.get('/api/v1/subscriptions')
def subscriptions(user=Depends(current_user), db=Depends(database)):
    return [{'id': s.id, 'name': s.name, 'filters': s.filters, 'unknown_policy': s.unknown_policy, 'enabled': s.enabled, 'reminder_hours': s.reminder_hours} for s in db.scalars(select(Subscription).where(Subscription.user_id == user.id))]

@app.post('/api/v1/subscriptions')
def subscribe(data: SubscriptionInput, user=Depends(current_user), db=Depends(database)):
    row = Subscription(user_id=user.id, name=data.name, filters=data.filters.model_dump(mode='json', exclude_none=True), unknown_policy=data.unknown_policy, enabled=data.enabled, reminder_hours=data.reminder_hours)
    db.add(row); db.commit()
    # Baseline shown as summary count, never enqueued as individual new events.
    counts = {'pass': 0, 'unknown': 0, 'fail': 0}
    from .resolution import grouped_rows
    for fields in grouped_rows(db):
        if fields: counts[match(fields, {**row.filters, 'registration_open': True})['verdict']] += 1
    return {'id': row.id, 'baseline': counts, 'message': '历史候选仅统计摘要；此后采集变化进入收件箱'}

@app.patch('/api/v1/subscriptions/{sid}')
def update_subscription(sid: int, data: SubscriptionInput, user=Depends(current_user), db=Depends(database)):
    row = db.get(Subscription, sid)
    if not row or row.user_id != user.id: raise HTTPException(404)
    row.name, row.filters, row.unknown_policy, row.enabled = data.name, data.filters.model_dump(mode='json', exclude_none=True), data.unknown_policy, data.enabled
    row.reminder_hours = data.reminder_hours
    from .notifications import cancel_invalid_reminders
    cancel_invalid_reminders(db)
    db.commit(); return {'ok': True}

@app.get('/api/v1/notifications')
def notifications(user=Depends(current_user), db=Depends(database)):
    rows = db.scalars(select(Outbox).join(Subscription).where(Subscription.user_id == user.id).order_by(Outbox.id.desc()).limit(100))
    return [{'id': r.id, 'state': r.state, 'read': r.read, 'created_at': r.created_at, **r.payload} for r in rows]

@app.patch('/api/v1/notifications/{nid}')
def read_notification(nid: int, user=Depends(current_user), db=Depends(database)):
    row = db.get(Outbox, nid)
    if not row or db.get(Subscription, row.subscription_id).user_id != user.id: raise HTTPException(404)
    row.read = True; db.commit(); return {'ok': True}

@app.get('/api/v1/sources')
def sources(user=Depends(current_user), db=Depends(database)):
    result = []
    for s in db.scalars(select(Source)):
        from .coverage import metrics
        job = db.scalar(select(Job).where(Job.source_id == s.id).order_by(Job.id.desc()).limit(1))
        result.append({'id': s.id, 'name': s.name, 'status': s.status, 'enabled': s.enabled, 'metrics': metrics(db, s),
                       'last_success_at': s.last_success_at, 'error': s.error, 'coverage': s.coverage,
                       'detail_last_success_at': s.detail_last_success_at, 'detail_checked': s.detail_checked,
                       'detail_next_run_at': s.detail_next_run_at, 'backfill_page': s.backfill_page, 'total_pages': s.total_pages, 'next_run_at': s.next_run_at,
                       'job': {'id': job.id, 'state': job.state, 'kind': job.kind, 'attempts': job.attempts,
                               'retry_at': job.retry_at, 'error': job.error} if job else None})
    return result

class SourceInput(BaseModel):
    enabled: bool

@app.patch('/api/v1/sources/{sid}')
def configure_source(sid: str, data: SourceInput, user=Depends(admin), db=Depends(database)):
    row = db.get(Source, sid)
    if not row: raise HTTPException(404)
    if sid == 'wzcqpt' and data.enabled: raise HTTPException(422, '适配器未实现')
    row.enabled = data.enabled; db.commit(); return {'ok': True}

@app.post('/api/v1/sources/{sid}/runs')
def source_run(sid: str, kind: str = 'front', user=Depends(admin), db=Depends(database)):
    if kind not in ('front', 'backfill', 'details'): raise HTTPException(422, '任务类型不支持')
    if sid not in ('nongjy', 'wzpt'): raise HTTPException(422, '适配器未实现')
    from .service import enqueue
    from .collectors import SourceError
    try:
        jid = enqueue(db, sid, kind)
    except SourceError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    row = db.get(Job, jid)
    return {'job_id': jid, 'state': row.state, 'kind': row.kind}

@app.get('/api/v1/jobs/{jid}')
def job_status(jid: int, user=Depends(admin), db=Depends(database)):
    row = db.get(Job, jid)
    if not row: raise HTTPException(404)
    return {'id': row.id, 'state': row.state, 'result': row.result, 'error': row.error, 'kind': row.kind, 'attempts': row.attempts, 'retry_at': row.retry_at}

@app.get('/api/v1/health/live')
def live(): return {'ok': True, 'mode': MODE}

@app.get('/api/v1/health/ready')
def ready(db=Depends(database)):
    from .email_delivery import settings
    db.execute(text('SELECT 1'))
    try: status = 'configured' if settings() else 'disabled'
    except (ValueError, TypeError): status = 'invalid_configuration'
    return {'database': 'ready', 'external_notifications': status}

@app.get('/api/v1/email-deliveries')
def email_deliveries(user=Depends(current_user), db=Depends(database)):
    from .db import EmailDelivery
    rows = db.scalars(select(EmailDelivery).join(Outbox).join(Subscription).where(
        Subscription.user_id == user.id).order_by(EmailDelivery.id.desc()).limit(100))
    return [{'id': r.id, 'notice_id': r.outbox_id, 'state': r.state, 'attempts': r.attempts,
             'retry_at': r.retry_at, 'accepted_at': r.accepted_at, 'error': r.error} for r in rows]

@app.get('/api/v1/source-alerts')
def source_alerts(user=Depends(current_user), db=Depends(database)):
    if user.role != 'admin': raise HTTPException(403)
    # Current incidents: stable source identity, no duplicate notices per polling cycle.
    return [{'id': 'source:' + row.id, 'source_id': row.id, 'status': row.status,
             'error': row.error, 'last_attempt_at': row.last_attempt_at,
             'last_success_at': row.last_success_at, 'paused': not row.enabled}
            for row in db.scalars(select(Source).where(Source.error.is_not(None)))]

from .workflows_api import router as workflows_router
app.include_router(workflows_router)

web = ROOT / 'frontend'
app.mount('/static', StaticFiles(directory=web), name='static')

@app.get('/')
def index(): return FileResponse(web / 'index.html', headers={'Cache-Control':'no-cache'})
