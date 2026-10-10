import hashlib
import secrets
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, text
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from .config import ROOT, MODE, COOKIE_SECURE
from .db import Session, User, LoginSession, Source, Job, Listing, Evidence, Version, RawDocument, Subscription, Outbox, Followup, CrawlRun
from .service import listing_data
from .domain import match

app = FastAPI(title='LeaseRadar', version='0.1.0')
hasher = PasswordHasher()
login_attempts = {}

def database():
    with Session() as db:
        yield db

def current_user(request: Request, db=Depends(database)):
    token = request.cookies.get('lease_session', '')
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
    response.set_cookie('lease_session', token, httponly=True, secure=COOKIE_SECURE, samesite='lax', max_age=43200)
    return {'username': user.username, 'role': user.role, 'csrf': csrf}

@app.get('/api/v1/auth/me')
def me(request: Request, user=Depends(current_user)):
    return {'username': user.username, 'role': user.role, 'csrf': request.state.session.csrf, 'mode': MODE}

@app.post('/api/v1/auth/logout')
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(database)):
    db.delete(db.get(LoginSession, request.state.session.token)); db.commit()
    response.delete_cookie('lease_session'); return {'ok': True}

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

@app.post('/api/v1/listings/search')
def search(data: SearchInput, user=Depends(current_user), db=Depends(database)):
    rows = []
    for listing in db.scalars(select(Listing).order_by(Listing.id.desc())):
        row = listing_data(db, listing, user.id)
        if not row: continue
        result = match(row, data.filters.model_dump(exclude_none=True))
        if result['verdict'] == 'fail' or (not data.include_unknown and result['verdict'] == 'unknown'): continue
        rows.append({**row, 'match': result})
    if data.sort == 'monthly':
        # Group price kind; unknown values sort last, never as zero.
        from decimal import Decimal
        rows.sort(key=lambda r: (r.get('price_kind', ''), r.get('first_year_monthly') is None, Decimal(r['first_year_monthly']) if r.get('first_year_monthly') else Decimal('Infinity')))
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
    return row

class CompareInput(BaseModel):
    listing_ids: list[int] = Field(min_length=2, max_length=5)

@app.post('/api/v1/comparisons')
def compare(data: CompareInput, user=Depends(current_user), db=Depends(database)):
    if len(set(data.listing_ids)) != len(data.listing_ids): raise HTTPException(422, '不能重复选择同一挂牌')
    rows = []
    for lid in data.listing_ids:
        listing = db.get(Listing, lid)
        if not listing: raise HTTPException(404, '挂牌不存在')
        rows.append(listing_data(db, listing, user.id))
    return {'items': rows, 'warning': '起始价、挂牌价分组比较；保证金不是租金，税费未知时无法得出最低总成本。'}

@app.get('/api/v1/exports/listings.csv')
def export(user=Depends(current_user), db=Depends(database)):
    import csv, io
    buf = io.StringIO(); buf.write('\ufeff')
    writer = csv.writer(buf)
    keys = ['id', 'title', 'address', 'area_m2', 'raw_amount', 'price_kind', 'period_basis', 'first_year_monthly', 'registration_deadline', 'source_url']
    writer.writerow(keys)
    for listing in db.scalars(select(Listing)):
        fields = listing_data(db, listing, user.id)
        if not fields: continue
        values = []
        for key in keys:
            value = str(fields.get(key) or '')
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
    db.commit(); return {'ok': True}

class SubscriptionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: Filters = Field(default_factory=Filters)
    unknown_policy: Literal['review_digest', 'exclude'] = 'review_digest'
    enabled: bool = True

@app.get('/api/v1/subscriptions')
def subscriptions(user=Depends(current_user), db=Depends(database)):
    return [{'id': s.id, 'name': s.name, 'filters': s.filters, 'unknown_policy': s.unknown_policy, 'enabled': s.enabled} for s in db.scalars(select(Subscription).where(Subscription.user_id == user.id))]

@app.post('/api/v1/subscriptions')
def subscribe(data: SubscriptionInput, user=Depends(current_user), db=Depends(database)):
    row = Subscription(user_id=user.id, name=data.name, filters=data.filters.model_dump(mode='json', exclude_none=True), unknown_policy=data.unknown_policy, enabled=data.enabled)
    db.add(row); db.commit()
    # Baseline shown as summary count, never enqueued as individual new events.
    counts = {'pass': 0, 'unknown': 0, 'fail': 0}
    for listing in db.scalars(select(Listing)):
        fields = listing_data(db, listing)
        if fields: counts[match(fields, {**row.filters, 'registration_open': True})['verdict']] += 1
    return {'id': row.id, 'baseline': counts, 'message': '历史候选仅统计摘要；此后采集变化进入收件箱'}

@app.patch('/api/v1/subscriptions/{sid}')
def update_subscription(sid: int, data: SubscriptionInput, user=Depends(current_user), db=Depends(database)):
    row = db.get(Subscription, sid)
    if not row or row.user_id != user.id: raise HTTPException(404)
    row.name, row.filters, row.unknown_policy, row.enabled = data.name, data.filters.model_dump(mode='json', exclude_none=True), data.unknown_policy, data.enabled
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
    return [{'id': s.id, 'name': s.name, 'status': s.status, 'enabled': s.enabled, 'last_success_at': s.last_success_at, 'error': s.error, 'coverage': s.coverage} for s in db.scalars(select(Source))]

class SourceInput(BaseModel):
    enabled: bool

@app.patch('/api/v1/sources/{sid}')
def configure_source(sid: str, data: SourceInput, user=Depends(admin), db=Depends(database)):
    row = db.get(Source, sid)
    if not row: raise HTTPException(404)
    if sid == 'wzcqpt' and data.enabled: raise HTTPException(422, '适配器未实现')
    row.enabled = data.enabled; db.commit(); return {'ok': True}

@app.post('/api/v1/sources/{sid}/runs')
def source_run(sid: str, user=Depends(admin), db=Depends(database)):
    if sid not in ('nongjy', 'wzpt'): raise HTTPException(422, '适配器未实现')
    from .service import enqueue
    jid = enqueue(db, sid); db.commit()
    return {'job_id': jid, 'state': 'queued'}

@app.get('/api/v1/jobs/{jid}')
def job_status(jid: int, user=Depends(admin), db=Depends(database)):
    row = db.get(Job, jid)
    if not row: raise HTTPException(404)
    return {'id': row.id, 'state': row.state, 'result': row.result, 'error': row.error}

@app.get('/api/v1/health/live')
def live(): return {'ok': True, 'mode': MODE}

@app.get('/api/v1/health/ready')
def ready(db=Depends(database)):
    db.execute(text('SELECT 1')); return {'database': 'ready', 'external_notifications': 'disabled'}

web = ROOT / 'frontend'
app.mount('/static', StaticFiles(directory=web), name='static')

@app.get('/')
def index(): return FileResponse(web / 'index.html')
