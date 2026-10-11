"""Human evidence is explicit and never presented as a fresh source observation."""
import hashlib
import json
from sqlalchemy import select
from .db import Version, Evidence, Correction, Listing, ListingRelation, AuditAction, now
from .domain import normalize_price, decimal

FIELDS = {'address','city','district','area_m2','raw_amount','price_kind','period_basis',
          'registration_deadline','auction_deadline','operation','property_type','environment','status','deposit'}

def publish(db, listing, previous, fields, quotes):
    fields = {**fields, **normalize_price(fields)}
    version = Version(listing_id=listing.id, raw_id=previous.raw_id, fields=fields,
        business_hash=hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        first_year_monthly=decimal(fields.get('first_year_monthly')), area_m2=decimal(fields.get('area_m2')))
    db.add(version); db.flush(); listing.current_version_id = version.id
    for item in db.scalars(select(Evidence).where(Evidence.version_id == previous.id)):
        if item.field not in quotes: db.add(Evidence(version_id=version.id,field=item.field,quote=item.quote,method=item.method))
    for field, quote in quotes.items(): db.add(Evidence(version_id=version.id, field=field, quote=quote, method='human_review'))
    from .notifications import cancel_invalid_reminders
    cancel_invalid_reminders(db)
    return version


def add_correction(db, listing, user_id, field, value, quote, reason):
    previous = db.get(Version, listing.current_version_id)
    if db.scalar(select(Correction.id).where(Correction.listing_id==listing.id,Correction.field==field,Correction.state.in_(['active','conflict']))):
        raise ValueError('该字段已有纠正，请先处理或撤销')
    row = Correction(listing_id=listing.id,user_id=user_id,field=field,value=value,
        original=previous.fields.get(field),quote=quote,reason=reason,base_version_id=previous.id)
    db.add(row); db.flush()
    fields={**previous.fields,field:value,'human_reviewed':True}
    row.version_id=publish(db,listing,previous,fields,{field:f'人工核验 #{row.id}：{quote}；原因：{reason}'}).id
    db.add(AuditAction(user_id=user_id,kind='correction_create',object_id=row.id,reason=reason))
    return row


def resolve_correction(db, row, user_id, action, reason):
    if row.state not in ('active','conflict'): raise ValueError('纠正已结束')
    listing=db.get(Listing,row.listing_id); previous=db.get(Version,listing.current_version_id)
    if action=='keep':
        row.state='active'
        fields={**previous.fields,'review_conflicts':[f for f in previous.fields.get('review_conflicts',[]) if f != row.field]}
        publish(db,listing,previous,fields,{row.field:f'人工继续核验 #{row.id}：{row.quote}；{reason}'})
        db.add(AuditAction(user_id=user_id,kind='correction_keep',object_id=row.id,reason=reason))
        return
    # base_version follows the latest source observation, even while manual value remains active.
    base=db.get(Version,row.base_version_id)
    fields={**previous.fields,row.field:base.fields.get(row.field),
            'review_conflicts':[f for f in previous.fields.get('review_conflicts',[]) if f != row.field]}
    publish(db,listing,previous,fields,{row.field:f'人工撤销 #{row.id}：恢复源观测版本 #{base.id}；{reason}'})
    row.state='reverted'; row.resolved_at=now()
    db.add(AuditAction(user_id=user_id,kind='correction_revert',object_id=row.id,reason=reason))


def retain_corrections(db, listing, source_version):
    rows=list(db.scalars(select(Correction).where(Correction.listing_id==listing.id,Correction.state.in_(['active','conflict']))))
    if not rows: return source_version
    fields=dict(source_version.fields);quotes={}
    for row in rows:
        base=db.get(Version,row.base_version_id)
        if source_version.fields.get(row.field)!=base.fields.get(row.field): row.state='conflict'
        row.base_version_id=source_version.id
        fields[row.field]=row.value
        quotes[row.field]=f'人工核验 #{row.id}：{row.quote}；来源更新{ "存在冲突待审" if row.state=="conflict" else "保留纠正" }'
    fields['human_reviewed']=True
    fields['review_conflicts']=[r.field for r in rows if r.state=='conflict']
    return publish(db,listing,source_version,fields,quotes)


def relation_data(db, listing_id):
    rows=db.scalars(select(ListingRelation).where((ListingRelation.left_id==listing_id)|(ListingRelation.right_id==listing_id)))
    return [{'id':r.id,'left_id':r.left_id,'right_id':r.right_id,'kind':r.kind,'state':r.state,'reason':r.reason,
             'created_at':r.created_at} for r in rows]
