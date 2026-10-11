from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
import pytest
from app.db import (Session,User,Subscription,Outbox,NotificationPreference,Digest,DigestItem,
    Version,Listing,Correction,SourceRecord,Source,Job,SourceIncident,ListingRelation,Event)
from app.service import ingest,deliver_local
from app.scheduling import quiet,dispatch_local,email_origins
from test_core import sample,client_for

AT=datetime(2026,10,11,0,tzinfo=timezone.utc) # 08:00 Shanghai

def notices(pref=None,count=2):
    with Session() as db:
        user=db.scalar(select(User).where(User.username=='member'))
        sub=Subscription(user_id=user.id,name='synthetic',filters={});db.add(sub);db.flush()
        for i in range(count):
            ingest(db,'nongjy',f'https://www.nongjy.cn/web/propertyBid/detail/{i+1}',sample());db.flush()
        for row in db.scalars(select(Outbox)):row.created_at=AT.isoformat()
        if pref:db.add(NotificationPreference(user_id=user.id,**pref))
        db.commit();return user.id


def test_daily_digest_window_membership_and_repeat():
    uid=notices({'mode':'daily','digest_time':'09:00'})
    dispatch_local(AT)
    with Session() as db:assert all(r.state=='queued' for r in db.scalars(select(Outbox)))
    dispatch_local(AT+timedelta(hours=1));dispatch_local(AT+timedelta(hours=1))
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Digest))==1
        assert db.scalar(select(func.count()).select_from(DigestItem))==2
        batch=db.scalar(select(Digest));assert batch.sources and batch.window_start==AT.isoformat()
        origins=[email_origins(db,r,AT+timedelta(hours=1)) for r in db.scalars(select(Outbox).order_by(Outbox.id))]
        assert list(map(len,origins))==[2,0]


def test_review_unknown_always_daily_when_preferences_saved():
    uid=notices({'mode':'instant'})
    with Session() as db:
        for row in db.scalars(select(Outbox)):row.payload={**row.payload,'delivery_class':'review_digest'}
        db.commit()
    dispatch_local(AT)
    with Session() as db:assert db.scalar(select(Outbox)).state=='queued'
    dispatch_local(AT+timedelta(hours=1))
    with Session() as db:assert db.scalar(select(Digest))

@pytest.mark.parametrize('clock,expected',[(21,False),(22,True),(0,True),(7,False)])
def test_quiet_cross_midnight(clock,expected):
    p=NotificationPreference(timezone='Asia/Shanghai',quiet_start='22:00',quiet_end='07:00')
    assert quiet(p,datetime(2026,10,11,clock,tzinfo=timezone(timedelta(hours=8)))) is expected


def test_quiet_delays_until_end_and_paused_sub_cancels():
    notices({'mode':'instant','quiet_start':'07:00','quiet_end':'10:00'})
    dispatch_local(AT+timedelta(hours=1))
    with Session() as db:
        assert db.scalar(select(Outbox)).state=='queued'
        db.scalar(select(Subscription)).enabled=False;db.commit()
    dispatch_local(AT+timedelta(hours=2))
    with Session() as db:assert all(r.state=='cancelled' for r in db.scalars(select(Outbox)))


def test_preferences_validation_and_user_isolation():
    c=client_for('member');o=client_for('other')
    assert c.put('/api/v1/notification-preferences',json={'timezone':'Not/AZone'}).status_code==422
    assert c.put('/api/v1/notification-preferences',json={'quiet_start':'22:00'}).status_code==422
    assert c.put('/api/v1/notification-preferences',json={'quiet_start':'22:00','quiet_end':'07:00','mode':'daily'}).status_code==200
    assert o.get('/api/v1/notification-preferences').json()['saved'] is False
    assert c.get('/api/v1/notification-preferences').json()['mode']=='daily'


def test_full_history_pagination_and_owner_counts():
    uid=notices(count=105)
    c=client_for('member');o=client_for('other')
    first=c.get('/api/v1/notifications/history?limit=100').json()
    second=c.get('/api/v1/notifications/history?page=2&limit=100').json()
    assert first['total']==first['unread']==105 and len(first['items'])==100 and len(second['items'])==5
    assert not set(r['id'] for r in first['items'])&set(r['id'] for r in second['items'])
    assert o.get('/api/v1/notifications/history').json()['total']==0
    assert c.get('/api/v1/notifications/history?limit=101').status_code==422


def seed_listing():
    with Session() as db:
        lid,_=ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
        return lid,db.get(Listing,lid).current_version_id


def test_manual_correction_reprocessing_conflict_and_revert():
    lid,version=seed_listing();c=client_for('admin')
    payload={'listing_id':lid,'base_version_id':version,'field':'raw_amount','value':'100000','quote':'电话核验：用户提供的金额记录','reason':'原始页面金额需要复核'}
    row=c.post('/api/v1/corrections',json=payload);assert row.status_code==200
    with Session() as db:
        checked=db.scalar(select(SourceRecord)).last_checked_at
        events=db.scalar(select(func.count()).select_from(Event))
        # Same input does not undo manual values or create a fake market event.
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
        assert db.get(Version,db.get(Listing,lid).current_version_id).fields['raw_amount']=='100000'
        assert db.scalar(select(func.count()).select_from(Event))==events
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample('90000'));db.commit()
        correction=db.get(Correction,row.json()['id']);assert correction.state=='conflict'
        assert db.get(Version,db.get(Listing,lid).current_version_id).fields['raw_amount']=='100000'
    review=c.get('/api/v1/review-queue').json()['items'][0]
    assert review['source_value']=='90000'
    r=c.post(f"/api/v1/corrections/{row.json()['id']}/resolve",json={'reason':'按最新原文恢复价格','action':'revert','expected_version_id':review['expected_version_id']})
    assert r.status_code==200
    assert c.get(f'/api/v1/listings/{lid}').json()['raw_amount']=='90000'


def test_correction_permissions_stale_version_and_value_validation():
    lid,version=seed_listing();c=client_for('admin');m=client_for('member')
    payload={'listing_id':lid,'base_version_id':version,'field':'area_m2','value':'61','quote':'面积由公开图纸核验','reason':'根据原文重新确定面积'}
    assert m.post('/api/v1/corrections',json=payload).status_code==403
    assert c.post('/api/v1/corrections',json={**payload,'value':'NaN'}).status_code==422
    assert c.post('/api/v1/corrections',json={**payload,'base_version_id':999}).status_code==409
    assert c.post('/api/v1/corrections',json=payload).status_code==200
    assert c.post('/api/v1/corrections',json=payload).status_code==409
    assert m.get('/api/v1/review-queue').status_code==403


def test_relationship_relisting_and_reversible_audit():
    seed_listing()
    with Session() as db:ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/2',sample());db.commit()
    c=client_for('admin');m=client_for('member')
    data={'left_id':2,'right_id':1,'kind':'relisting','reason':'公告明确描述原项目重新挂牌'}
    assert m.post('/api/v1/listing-relations',json=data).status_code==403
    r=c.post('/api/v1/listing-relations',json=data);assert r.status_code==200
    assert c.post('/api/v1/listing-relations',json=data).status_code==409
    assert c.get('/api/v1/listing-relations/1').json()[0]['kind']=='relisting'
    assert c.post(f"/api/v1/listing-relations/{r.json()['id']}/revert",json={'reason':'复核发现编号属于不同资产'}).status_code==200
    with Session() as db:
        assert db.scalar(select(ListingRelation)).state=='reverted'
        assert db.scalar(select(func.count()).select_from(Listing))==2


def test_incident_lifecycle_dedup_and_disabled_freshness():
    from app.coverage import sync_incidents
    with Session() as db:
        source=db.get(Source,'nongjy');source.enabled=True;source.error='HTTP 403';db.commit()
    sync_incidents(AT);sync_incidents(AT)
    with Session() as db:assert db.scalar(select(func.count()).select_from(SourceIncident))==2
    with Session() as db:
        source=db.get(Source,'nongjy');source.enabled=False;source.error=None;db.commit()
    sync_incidents(AT+timedelta(hours=1))
    with Session() as db:assert all(r.state=='resolved' for r in db.scalars(select(SourceIncident)))


def test_expired_source_owner_cannot_renew_or_overwrite_new_worker():
    from app.service import renew_source
    from app.collectors import SourceError
    with Session() as db:
        source=db.get(Source,'nongjy');source.lease_token='new';source.lease_until=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat();db.commit()
        with pytest.raises(SourceError):renew_source(db,'nongjy','old')
        db.rollback();assert db.get(Source,'nongjy').lease_token=='new'
        source=db.get(Source,'nongjy');source.lease_token='old';source.lease_until='2000-01-01T00:00:00+00:00';db.commit()
        with pytest.raises(SourceError):renew_source(db,'nongjy','old')


def test_source_takeover_during_network_call_does_not_ingest(monkeypatch):
    import app.service as service
    def fetch(url):
        if 'detail' in url:
            with Session() as db:
                source=db.get(Source,'nongjy');source.lease_token='new-owner';source.error='new error';db.commit()
            return sample()
        return 'list'
    monkeypatch.setattr(service,'fetch',fetch)
    monkeypatch.setitem(service.DISCOVERERS,'nongjy',lambda *args: (['https://www.nongjy.cn/web/propertyBid/detail/1'],1))
    with pytest.raises(Exception):service.crawl('nongjy',delay=0)
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Listing))==0
        assert db.get(Source,'nongjy').error=='new error'


def test_coverage_counts_actual_page_and_policy_permission():
    from app.coverage import observe_page,metrics
    with Session() as db:
        observe_page(db,'nongjy',2);db.flush();observe_page(db,'nongjy',2);db.commit()
        assert metrics(db,db.get(Source,'nongjy'))['pages_today']==1
    c=client_for('admin');m=client_for('member')
    assert m.put('/api/v1/sources/nongjy/coverage-policy',json={}).status_code==403
    assert c.put('/api/v1/sources/nongjy/coverage-policy',json={'daily_page_budget':241}).status_code==422
    assert c.put('/api/v1/sources/nongjy/coverage-policy',json={'daily_page_budget':120,'backfill_batch_pages':4}).status_code==200
    assert c.get('/api/v1/sources').json()[0]['metrics']['daily_page_budget']==120


def test_source_grouping_unknown_conflicts_and_revert():
    seed_listing()
    with Session() as db:ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/2',sample('90000'));db.commit()
    c=client_for('admin')
    relation=c.post('/api/v1/listing-relations',json={'left_id':1,'right_id':2,'kind':'same_round','reason':'复核两个公告确属同一挂牌'}).json()
    rows=c.post('/api/v1/listings/search',json={}).json();assert rows['total']==1
    r=rows['items'][0];assert r['source_count']==2 and r['raw_amount'] is None
    assert 'raw_amount' in r['source_conflicts'] and r['match']['verdict']=='unknown'
    assert len(c.get('/api/v1/listings/2').json()['source_variants'])==2
    c.post(f"/api/v1/listing-relations/{relation['id']}/revert",json={'reason':'撤销人工合并，重新分开核验'})
    assert c.post('/api/v1/listings/search',json={}).json()['total']==2


def test_grouped_search_uses_bounded_query_count():
    from app.db import engine
    from sqlalchemy import event
    notices(count=50)
    c=client_for('member');calls=[]
    def count(*args):calls.append(1)
    event.listen(engine,'before_cursor_execute',count)
    try:
        assert c.post('/api/v1/listings/search',json={}).json()['total']==50
    finally:event.remove(engine,'before_cursor_execute',count)
    assert len(calls)<=8 # Auth + batch queries; no one-query-per-listing.


def test_conflicted_manual_values_never_clear_match_and_keep_resolves():
    from app.domain import match
    lid,vid=seed_listing();c=client_for('admin')
    r=c.post('/api/v1/corrections',json={'listing_id':lid,'base_version_id':vid,'field':'area_m2','value':'65','quote':'公开测量面积记录为65平米','reason':'测量结果与源页面面积不同'})
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample().replace('约60㎡','约70㎡'));db.commit()
        v=db.get(Version,db.get(Listing,lid).current_version_id)
        assert match(v.fields,{})['verdict']=='unknown'
    q=c.get('/api/v1/review-queue').json()['items'][0]
    assert c.post(f"/api/v1/corrections/{r.json()['id']}/resolve",json={'action':'keep','reason':'再次测量确认人工值仍有效','expected_version_id':q['expected_version_id']}).status_code==200
    assert c.post('/api/v1/listings/search',json={}).json()['items'][0]['match']['verdict']=='pass'


def test_pin_dns_to_validated_address_and_keep_tls_hostname(monkeypatch):
    from app import collectors
    from contextlib import contextmanager
    import httpx
    calls=[]
    monkeypatch.setattr(collectors.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('8.8.8.8',443))])
    class Client:
        def __init__(self,**kwargs):calls.append(kwargs)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        @contextmanager
        def stream(self,method,url,**kwargs):
            calls.append((str(url),kwargs));yield httpx.Response(200,headers={'content-type':'text/html'},content=b'<html>synthetic</html>')
    monkeypatch.setattr(collectors.httpx,'Client',Client)
    assert 'synthetic' in collectors.fetch('https://www.nongjy.cn/web/propertyBid/list')
    assert calls[0]['headers']['Host']=='www.nongjy.cn' and calls[0]['follow_redirects'] is False
    assert calls[1][0].startswith('https://8.8.8.8/') and calls[1][1]['extensions']['sni_hostname']=='www.nongjy.cn'


def test_evaluation_counts_unknown_coverage_and_leakage():
    from app.evaluation import evaluate
    rows=[{'id':1,'source':'synthetic','group':'one','split':'holdout','expected':{'area_m2':'60','period_basis':None},'predicted':{'area_m2':None,'period_basis':'first_year'}}]
    result=evaluate(rows)
    assert result['fields']['area_m2']['coverage']==0 and result['fields']['area_m2']['known_truth_recall']==0
    assert result['fields']['period_basis']['false_known_on_unknown']==1 and result['fields']['period_basis']['precision']==0
    with pytest.raises(ValueError):evaluate(rows+[{**rows[0],'id':2,'split':'development'}])


def test_readiness_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv('SMTP_PASSWORD','synthetic-password-secret')
    c=client_for('admin');m=client_for('member')
    r=c.get('/api/v1/setup-readiness');assert r.status_code==200 and 'synthetic-password-secret' not in r.text
    assert m.get('/api/v1/setup-readiness').status_code==403


def test_import_is_durable_and_rejects_unreviewed_urls():
    c=client_for('admin');m=client_for('member')
    assert m.post('/api/v1/imports',json={'url':'https://www.nongjy.cn/web/propertyBid/detail/1'}).status_code==403
    assert c.post('/api/v1/imports',json={'url':'https://127.0.0.1/secret'}).status_code==422
    assert c.post('/api/v1/imports',json={'url':'https://www.nongjy.cn/web/propertyBid/list'}).status_code==422
    response=c.post('/api/v1/imports',json={'url':'https://www.nongjy.cn/web/propertyBid/detail/1'})
    assert response.status_code==200
    with Session() as db:
        job=db.get(Job,response.json()['job_id']);assert job.kind=='import' and job.state=='queued'
        assert db.get(Source,'nongjy').enabled is False


def test_digest_smtp_sends_once_per_batch(monkeypatch):
    from app.email_delivery import deliver_email
    uid=notices({'mode':'daily'})
    dispatch_local(AT+timedelta(hours=1))
    monkeypatch.setenv('EMAIL_ENABLED','true');monkeypatch.setenv('EMAIL_USER_ID',str(uid))
    monkeypatch.setenv('EMAIL_RECIPIENT','synthetic@example.test');monkeypatch.setenv('SMTP_FROM','sender@example.test')
    monkeypatch.setenv('SMTP_HOST','127.0.0.1');monkeypatch.setenv('SMTP_SECURITY','local');monkeypatch.setenv('EMAIL_START_AT',AT.isoformat())
    received=[]
    def sender(config,message):received.append(message);return 'accepted',None
    assert deliver_email(AT+timedelta(hours=1),sender=sender)==1
    assert deliver_email(AT+timedelta(hours=1),sender=sender)==0
    assert len(received)==1 and received[0]['Subject']=='LeaseRadar 每日摘要'


def test_quiet_blocks_external_already_accepted_notice(monkeypatch):
    from app.email_delivery import eligible
    notices({'mode':'instant','quiet_start':'10:00','quiet_end':'12:00'},count=1)
    dispatch_local(AT)
    with Session() as db:
        notice=db.scalar(select(Outbox));assert notice.state=='accepted'
        assert eligible(db,notice,AT+timedelta(hours=2)) is False
        assert eligible(db,notice,AT+timedelta(hours=4)) is True


def test_same_round_compare_and_pending_notices_are_not_double_counted():
    notices(count=2)
    c=client_for('admin')
    assert c.post('/api/v1/listing-relations',json={'left_id':1,'right_id':2,'kind':'same_round','reason':'两个合成公告经人工确认同一挂牌'}).status_code==200
    assert c.post('/api/v1/comparisons',json={'listing_ids':[1,2]}).status_code==422
    with Session() as db:
        rows=list(db.scalars(select(Outbox).order_by(Outbox.id)))
        assert rows[1].state=='cancelled' and rows[0].state=='queued'
