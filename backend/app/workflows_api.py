"""Authenticated workflow endpoints. Imported after auth dependencies are defined."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal, Any
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, func, update
from .main import database, current_user, admin
from .db import (NotificationPreference, Outbox, Subscription, EmailDelivery, Digest, DigestItem,
                 Correction, Version, Listing, ListingRelation, AuditAction, SourceIncident, now)
from .domain import decimal, aware_time
from .review import FIELDS, add_correction, resolve_correction, relation_data
router=APIRouter(prefix='/api/v1')

class PreferenceInput(BaseModel):
    mode: Literal['instant','daily']='instant'
    timezone: str='Asia/Shanghai'
    digest_time: str='09:00'
    quiet_start: str | None=None
    quiet_end: str | None=None
    urgent_override: bool=False
    @model_validator(mode='after')
    def valid(self):
        try: ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError): raise ValueError('请选择有效时区')
        for value in [self.digest_time,self.quiet_start,self.quiet_end]:
            if value is not None and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value): raise ValueError('时间须为HH:MM')
        if bool(self.quiet_start)!=bool(self.quiet_end) or self.quiet_start is not None and self.quiet_start==self.quiet_end:
            raise ValueError('静默时间须填写不同的开始与结束，或同时留空')
        return self

@router.get('/notification-preferences')
def preferences(user=Depends(current_user),db=Depends(database)):
    row=db.get(NotificationPreference,user.id)
    return {**PreferenceInput().model_dump(), 'saved':False} if not row else {**{k:getattr(row,k) for k in PreferenceInput.model_fields},'saved':True}

@router.put('/notification-preferences')
def set_preferences(data:PreferenceInput,user=Depends(current_user),db=Depends(database)):
    row=db.get(NotificationPreference,user.id)
    if not row: row=NotificationPreference(user_id=user.id);db.add(row)
    for key,value in data.model_dump().items():setattr(row,key,value)
    db.commit();return {'ok':True,'message':'待确认候选每日汇总；原始发现时间保留，静默期间延后发送'}

@router.get('/notifications/history')
def history(page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),state:str|None=None,unread:bool=False,user=Depends(current_user),db=Depends(database)):
    query=select(Outbox).join(Subscription).where(Subscription.user_id==user.id)
    if state:query=query.where(Outbox.state==state)
    if unread:query=query.where(Outbox.read.is_(False),Outbox.state!='cancelled')
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    count=db.scalar(select(func.count()).select_from(Outbox).join(Subscription).where(Subscription.user_id==user.id,Outbox.read.is_(False),Outbox.state!='cancelled'))
    items=[{'id':r.id,'state':r.state,'read':r.read,'created_at':r.created_at,**r.payload} for r in db.scalars(query.order_by(Outbox.id.desc()).offset((page-1)*limit).limit(limit))]
    return {'items':items,'total':total,'page':page,'unread':count}

@router.get('/email-deliveries/history')
def email_history(page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),user=Depends(current_user),db=Depends(database)):
    query=select(EmailDelivery).join(Outbox).join(Subscription).where(Subscription.user_id==user.id)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    items=[{'id':r.id,'notice_id':r.outbox_id,'state':r.state,'attempts':r.attempts,'retry_at':r.retry_at,'accepted_at':r.accepted_at,'error':r.error} for r in db.scalars(query.order_by(EmailDelivery.id.desc()).offset((page-1)*limit).limit(limit))]
    return {'items':items,'total':total,'page':page}

@router.get('/digests')
def digests(page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),user=Depends(current_user),db=Depends(database)):
    query=select(Digest).where(Digest.user_id==user.id)
    rows=list(db.scalars(query.order_by(Digest.id.desc()).offset((page-1)*limit).limit(limit)))
    return {'total':db.scalar(select(func.count()).select_from(query.subquery())), 'items':[
        {'id':d.id,'window_start':d.window_start,'window_end':d.window_end,'sources':d.sources,
         'notice_ids':list(db.scalars(select(DigestItem.outbox_id).where(DigestItem.digest_id==d.id))),
         'items':[{'id':n.id,'title':n.payload.get('title'),'listing_id':n.payload.get('listing_id'),'state':n.state} for n in db.scalars(select(Outbox).join(DigestItem).where(DigestItem.digest_id==d.id))]} for d in rows]}

class CorrectionInput(BaseModel):
    listing_id:int
    base_version_id:int
    field:str
    value:Any=None
    quote:str=Field(min_length=5,max_length=3000)
    reason:str=Field(min_length=5,max_length=1000)
    @model_validator(mode='after')
    def valid(self):
        if len(self.quote.strip())<5 or len(self.reason.strip())<5:raise ValueError('依据和原因不能只填空格')
        if self.field not in FIELDS:raise ValueError('不支持此纠正字段')
        if self.value is None:return self
        if isinstance(self.value,bool) or not isinstance(self.value,(str,int)):raise ValueError('值须为文本或整数，金额建议字符串')
        enums={'price_kind':{'starting_bid','asking','sale'},'period_basis':{'first_year','monthly'},
            'status':{'open','closed','withdrawn','sold','failed','unknown'},'operation':{'coffee_beverage','restaurant','retail'},
            'property_type':{'shop','commercial_unit','office','warehouse','apartment'},'environment':{'campus','apartment_building','street','market'}}
        if self.field in enums and self.value not in enums[self.field]:raise ValueError('字段选项无效')
        if self.field in {'area_m2','raw_amount','deposit'}:
            try:value=decimal(self.value)
            except Exception:raise ValueError('数值无效')
            if value is None or not value.is_finite() or value<0 or value>100000000000000 or value.as_tuple().exponent < -8:raise ValueError('须填写非负有效数字')
            self.value=str(value)
        elif self.field.endswith('_deadline'):
            value=aware_time(self.value)
            if value is None:raise ValueError('截止时间必须带时区')
            self.value=value.isoformat()
        elif not isinstance(self.value,str) or not self.value.strip() or len(self.value)>2000:raise ValueError('文本无效')
        return self

class ResolveInput(BaseModel):
    action:Literal['keep','revert']='revert'
    reason:str=Field(min_length=5,max_length=1000)
    expected_version_id:int

@router.post('/corrections')
def create_correction(data:CorrectionInput,user=Depends(admin),db=Depends(database)):
    listing=db.get(Listing,data.listing_id)
    if not listing:raise HTTPException(404)
    if not db.execute(update(Listing).where(Listing.id==listing.id,Listing.current_version_id==data.base_version_id).values(current_version_id=data.base_version_id)).rowcount:raise HTTPException(409,'公告版本已变化，请刷新依据')
    try:row=add_correction(db,listing,user.id,data.field,data.value,data.quote,data.reason)
    except ValueError as exc:raise HTTPException(409,str(exc))
    db.commit();return {'id':row.id,'version_id':listing.current_version_id}

@router.post('/corrections/{cid}/resolve')
def resolve(cid:int,data:ResolveInput,user=Depends(admin),db=Depends(database)):
    row=db.get(Correction,cid)
    if not row:raise HTTPException(404)
    if not db.execute(update(Listing).where(Listing.id==row.listing_id,Listing.current_version_id==data.expected_version_id).values(current_version_id=data.expected_version_id)).rowcount:raise HTTPException(409,'当前版本已变化，请刷新')
    try:resolve_correction(db,row,user.id,data.action,data.reason)
    except ValueError as exc:raise HTTPException(409,str(exc))
    db.commit();return {'ok':True}

@router.get('/review-queue')
def review_queue(page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),user=Depends(admin),db=Depends(database)):
    query=select(Correction).order_by(Correction.id.desc())
    rows=list(db.scalars(query.offset((page-1)*limit).limit(limit)))
    from .resolution import grouped_rows
    conflicts=[r for r in grouped_rows(db) if r['source_conflicts']]
    return {'total':db.scalar(select(func.count()).select_from(Correction)),
        'source_conflict_total':len(conflicts),'source_conflicts':[{k:r[k] for k in ('id','title','source_conflicts','source_variants')} for r in conflicts[(page-1)*limit:page*limit]], 'items':[
        {'id':r.id,'listing_id':r.listing_id,'field':r.field,'value':r.value,'original':r.original,'quote':r.quote,'reason':r.reason,
         'state':r.state,'source_value':db.get(Version,r.base_version_id).fields.get(r.field),
         'expected_version_id':db.get(Listing,r.listing_id).current_version_id} for r in rows]}

class RelationInput(BaseModel):
    left_id:int
    right_id:int
    kind:Literal['same_round','relisting','same_asset','bundle_member']
    reason:str=Field(min_length=5,max_length=1000)

@router.post('/listing-relations')
def relation(data:RelationInput,user=Depends(admin),db=Depends(database)):
    left,right=sorted([data.left_id,data.right_id])
    if left==right:raise HTTPException(422,'不能关联自身')
    if not db.get(Listing,left) or not db.get(Listing,right):raise HTTPException(404)
    row=db.scalar(select(ListingRelation).where(ListingRelation.left_id==left,ListingRelation.right_id==right,ListingRelation.kind==data.kind))
    if row and row.state=='active':raise HTTPException(409,'关联已存在')
    if not row:row=ListingRelation(left_id=left,right_id=right,kind=data.kind,user_id=user.id,reason=data.reason);db.add(row);db.flush()
    else:row.state='active';row.reason=data.reason;row.user_id=user.id;row.resolved_at=None
    db.add(AuditAction(user_id=user.id,kind='relation_create',object_id=row.id,reason=data.reason))
    if data.kind=='same_round':
        from .resolution import grouped_rows
        from .domain import match
        from .notifications import cancel_invalid_reminders
        db.flush()
        group=next(g for g in grouped_rows(db) if left in g['related_listing_ids'])
        for notice in db.scalars(select(Outbox).where(Outbox.state=='queued')):
            lid=notice.payload.get('listing_id')
            if lid not in group['related_listing_ids']:continue
            if lid!=group['id']:notice.state='cancelled';continue
            sub=db.get(Subscription,notice.subscription_id)
            result=match(group,{**sub.filters,'registration_open':True})
            if result['verdict']=='fail' or result['verdict']=='unknown' and sub.unknown_policy=='exclude':notice.state='cancelled'
            else:notice.payload={**notice.payload,'match':result,'delivery_class':'instant' if result['verdict']=='pass' else 'review_digest'}
        cancel_invalid_reminders(db)
    db.commit();return {'id':row.id}

@router.get('/listing-relations/{lid}')
def relations(lid:int,user=Depends(current_user),db=Depends(database)):
    return relation_data(db,lid)

class RevertRelation(BaseModel):
    reason:str=Field(min_length=5,max_length=1000)
@router.post('/listing-relations/{rid}/revert')
def revert_relation(rid:int,data:RevertRelation,user=Depends(admin),db=Depends(database)):
    row=db.get(ListingRelation,rid)
    if not row:raise HTTPException(404)
    if row.state!='active':raise HTTPException(409,'关联已撤销')
    row.state='reverted';row.resolved_at=now()
    db.add(AuditAction(user_id=user.id,kind='relation_revert',object_id=row.id,reason=data.reason));db.commit();return {'ok':True}

@router.get('/source-incidents')
def incidents(page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),user=Depends(admin),db=Depends(database)):
    rows=db.scalars(select(SourceIncident).order_by(SourceIncident.id.desc()).offset((page-1)*limit).limit(limit))
    return {'total':db.scalar(select(func.count()).select_from(SourceIncident)), 'items':[{'id':r.id,'source_id':r.source_id,'kind':r.kind,'state':r.state,'message':r.message,'opened_at':r.opened_at,'resolved_at':r.resolved_at} for r in rows]}

class CoveragePolicy(BaseModel):
    daily_page_budget:int=Field(default=48,ge=1,le=240)
    backfill_batch_pages:int=Field(default=3,ge=1,le=10)
@router.put('/sources/{sid}/coverage-policy')
def coverage_policy(sid:str,data:CoveragePolicy,user=Depends(admin),db=Depends(database)):
    from .db import Source
    row=db.get(Source,sid)
    if not row:raise HTTPException(404)
    for key,value in data.model_dump().items():setattr(row,key,value)
    db.commit();return {'ok':True}

@router.get('/setup-readiness')
def setup_readiness(user=Depends(admin),db=Depends(database)):
    from .readiness import inventory
    return inventory(db)

class ImportInput(BaseModel):
    url:str=Field(max_length=2000)
@router.post('/imports')
def import_link(data:ImportInput,user=Depends(admin),db=Depends(database)):
    from urllib.parse import urlsplit
    from .db import Job
    try:parsed=urlsplit(data.url);port=parsed.port
    except ValueError:raise HTTPException(422,'URL格式或端口无效')
    if parsed.scheme!='https' or parsed.username or parsed.password or port not in (None,443):raise HTTPException(422,'只允许核准HTTPS公开详情链接')
    if parsed.hostname=='www.nongjy.cn' and re.fullmatch(r'/web/propertyBid/detail/\d+',parsed.path):sid='nongjy'
    elif parsed.hostname=='www.wzpt.edu.cn' and re.search(r'/c\d+a\d+/page\.htm$',parsed.path):sid='wzpt'
    else:raise HTTPException(422,'该详情URL暂无已验证适配器；不会抓取任意外链')
    if db.scalar(select(Job.id).where(Job.source_id==sid,Job.state.in_(['queued','running','retry_wait']))):raise HTTPException(409,'来源已有任务，请完成后再导入')
    job=Job(source_id=sid,kind='import',result={'requested_url':data.url});db.add(job);db.commit()
    return {'job_id':job.id,'state':job.state,'message':'已进入持久任务队列；网络受阻不会绕过访问控制'}

@router.get('/audit-actions')
def audit_history(page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),user=Depends(admin),db=Depends(database)):
    rows=db.scalars(select(AuditAction).order_by(AuditAction.id.desc()).offset((page-1)*limit).limit(limit))
    return {'total':db.scalar(select(func.count()).select_from(AuditAction)),'items':[
        {'id':r.id,'user_id':r.user_id,'kind':r.kind,'object_id':r.object_id,'reason':r.reason,'created_at':r.created_at} for r in rows]}
