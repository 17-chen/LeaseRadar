"""Explicit source grouping without destructive merging or invented price splits."""
from sqlalchemy import select
from .db import ListingRelation, Version, Listing, SourceRecord, Followup
from .domain import normalize_price
KEYS=('address','city','district','area_m2','raw_amount','price_kind','period_basis','registration_deadline',
      'auction_deadline','status','operation','property_type','environment','deposit')

def groups(db):
    parent={}
    def root(a):
        parent.setdefault(a,a)
        while parent[a]!=a:a=parent[a]
        return a
    for r in db.scalars(select(ListingRelation).where(ListingRelation.kind=='same_round',ListingRelation.state=='active')):
        a,b=root(r.left_id),root(r.right_id);parent[max(a,b)]=min(a,b)
    return {a:root(a) for a in parent}


def grouped_rows(db, user_id=None):
    """Batch loading replaces the previous per-listing SQL round trips."""
    listings=list(db.scalars(select(Listing).order_by(Listing.id.desc())))
    ids=[l.current_version_id for l in listings if l.current_version_id]
    versions={v.id:v for v in db.scalars(select(Version).where(Version.id.in_(ids)))}
    records={r.listing_id:r for r in db.scalars(select(SourceRecord))}
    followups={f.listing_id:f for f in db.scalars(select(Followup).where(Followup.user_id==user_id))} if user_id else {}
    mapping=groups(db);bundles={}
    for listing in listings:
        v=versions.get(listing.current_version_id);record=records.get(listing.id)
        if not v or not record:continue
        followup=followups.get(listing.id)
        row={'id':listing.id,**v.fields,'version_id':v.id,'source_id':record.source_id,'last_checked_at':record.last_checked_at,
             'created_at':listing.created_at,'followup':{'status':followup.status,'note':followup.note,'favorite':followup.favorite} if followup else None}
        bundles.setdefault(mapping.get(listing.id,listing.id),[]).append(row)
    result=[]
    for canonical,variants in bundles.items():
        primary=next(r for r in variants if r['id']==canonical);merged=dict(primary);conflicts=[]
        for key in KEYS:
            known=[v[key] for v in variants if v.get(key) not in (None,'','unknown')]
            distinct=set(map(str,known))
            if len(distinct)>1:merged[key]=None;conflicts.append(key)
            elif known:merged[key]=known[0]
        merged.update(normalize_price(merged))
        merged['source_conflicts']=conflicts
        merged['review_conflicts']=list(set(conflicts+sum((v.get('review_conflicts',[]) for v in variants),[])))
        merged['source_count']=len(variants)
        merged['related_listing_ids']=[v['id'] for v in variants]
        # Preserve personal actions on non-canonical sources without merging notes.
        merged['personal_followups']=[{'listing_id':v['id'], 'status':v['followup']['status'],
                                      'favorite':v['followup']['favorite']}
                                     for v in variants if v.get('followup')]
        merged['source_variants']=[{k:v.get(k) for k in ('id','version_id','title','source_url','source_id',*KEYS)} for v in variants]
        result.append(merged)
    return sorted(result,key=lambda r:r['id'],reverse=True)
