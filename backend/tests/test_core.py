from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from app.domain import normalize_price, match
from app.collectors import nongjy_parse, nongjy_discover, validate_url, SourceError
from app.db import Session, User, Listing, Version, Outbox, Event, Subscription
from app.service import ingest, deliver_local
from app.main import app

def sample(price='120000.00'):
    return f'''<html><div><div class="cont-info-left-title">合成样例：测试路11号商铺五年租赁权</div>
    <div><span class="cont-info-left-bt">项目位置：</span><span>测试市测试区测试路11号</span></div>
    <div><span class="cont-info-left-bt">交易单位：</span>约60㎡</div>
    <div>起始价<span class="cont-info-left-timebox-price">{price}</span>元</div>
    <div class="signupButton">报名交保证金</div>
    报名截止时间：2099-10-16 16:00:00 竞价截止时间：2099-10-18 10:00:00</div></html>'''

def test_price_period_unknown_is_not_five_year_total():
    f, _, _ = nongjy_parse(sample(), 'https://www.nongjy.cn/web/propertyBid/detail/1')
    assert normalize_price(f)['first_year_monthly'] is None

def test_decimal_price_and_area():
    p = normalize_price({'raw_amount':'120000', 'area_m2':'60', 'period_basis':'first_year'})
    assert p['first_year_monthly'] == '10000.00'
    assert p['unit_monthly'] == '166.67'
    assert p['cost_complete'] is False

@pytest.mark.parametrize('area', ['30', '100'])
def test_inclusive_bounds(area):
    assert match({'area_m2':area}, {'area_m2_min':'30', 'area_m2_max':'100'})['verdict']=='pass'

def test_unknown_use_never_passes_coffee():
    assert match({'operation':None}, {'operation':'coffee_beverage'})['verdict']=='unknown'

def test_registration_not_auction():
    fields={'registration_deadline':'2026-10-16T16:00:00+08:00','auction_deadline':'2026-10-18T10:00:00+08:00'}
    assert match(fields, {'registration_open':True}, datetime(2026,10,17,tzinfo=timezone.utc))['verdict']=='fail'

def test_abnormal_empty_list_fails():
    with pytest.raises(SourceError): nongjy_discover('<html>Maintenance</html>')

@pytest.mark.parametrize('url', ['https://127.0.0.1/', 'http://www.nongjy.cn/', 'https://www.nongjy.cn.evil.test/', 'https://user@www.nongjy.cn/', 'https://www.nongjy.cn:8080/'])
def test_ssrf_rejects_url(url):
    with pytest.raises(SourceError): validate_url(url)

def test_repeat_crawl_and_notification_idempotency():
    with Session() as db:
        u=db.scalar(select(User).where(User.username=='member'))
        db.add(Subscription(user_id=u.id,name='all',filters={},unknown_policy='review_digest'));db.commit()
        for _ in range(2): ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
        assert db.scalar(select(func.count()).select_from(Listing))==1
        assert db.scalar(select(func.count()).select_from(Version))==1
        assert db.scalar(select(func.count()).select_from(Outbox))==1
        row=db.scalar(select(Outbox));assert row.payload['match']['verdict']=='pass'
        db.add(Outbox(subscription_id=row.subscription_id,event_id=row.event_id,payload={}))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
    deliver_local();deliver_local()
    with Session() as db: assert db.scalar(select(Outbox)).state=='accepted'

def test_price_reverts_to_earlier_value_keeps_new_version():
    with Session() as db:
        for amount in ['120000','100000','120000']:
            ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample(amount));db.commit()
        assert db.scalar(select(func.count()).select_from(Version))==3

def client_for(name):
    c=TestClient(app)
    r=c.post('/api/v1/auth/login',json={'username':name,'password':'test-password-123'})
    assert r.status_code==200
    c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def test_permissions_csrf_and_session():
    c=client_for('member')
    assert c.patch('/api/v1/sources/nongjy',json={'enabled':True}).status_code==403
    c.headers.pop('X-CSRF-Token')
    assert c.post('/api/v1/subscriptions',json={'name':'x','filters':{}}).status_code==403
    assert TestClient(app).get('/api/v1/listings/1').status_code==401

def test_subscription_user_isolation_and_baseline():
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
    c=client_for('member');r=c.post('/api/v1/subscriptions',json={'name':'my filter','filters':{'area_m2_min':'30'}})
    assert r.status_code==200 and r.json()['baseline']['pass']==1
    with Session() as db: assert db.scalar(select(func.count()).select_from(Outbox))==0
    other=client_for('other');assert other.get('/api/v1/subscriptions').json()==[]
    assert other.patch('/api/v1/subscriptions/'+str(r.json()['id']),json={'name':'stolen','filters':{}}).status_code==404

def test_filter_validation_and_safe_detail():
    c=client_for('member')
    assert c.post('/api/v1/listings/search',json={'filters':{'area_m2_min':100,'area_m2_max':30}}).status_code==422
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
    detail=c.get('/api/v1/listings/1');assert detail.status_code==200
    assert detail.json()['evidence'] and detail.json()['first_year_monthly'] is None

def test_docx_lot_identity_and_price_conflict():
    from app.attachments import enrich_tables
    tables=[[['标的编号','标的概况','首年租金起始价'],['1','测试路11号商铺','120000元'],['2','测试路111号商铺','10000元']]]
    f={'title':'标的1：测试路11号商铺','raw_amount':'120000','warnings':[]};e={}
    assert enrich_tables(f,e,tables,'https://www.nongjy.cn/file.docx')
    assert f['period_basis']=='first_year' and '行2' in e['period_basis']
    f={'title':'测试路111号商铺','raw_amount':'120000','warnings':[]}
    assert not enrich_tables(f,{},tables,'https://www.nongjy.cn/file.docx')
    assert 'period_basis' not in f

def test_docx_rejects_entity_or_nonzip():
    from app.attachments import docx_tables
    with pytest.raises(SourceError): docx_tables(b'<html>error</html>')

def test_historical_disclosure_not_recommended():
    assert match({'disclosure_deadline':'2025-07-23'}, {'registration_open':True})['verdict']=='fail'

def test_comparison_missing_price_and_csv_injection():
    c=client_for('member')
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/2',sample().replace('合成样例：','=HYPERLINK '));db.commit()
    r=c.post('/api/v1/comparisons',json={'listing_ids':[1,2]})
    assert r.status_code==200 and all(x['first_year_monthly'] is None for x in r.json()['items'])
    assert "'=HYPERLINK" in c.get('/api/v1/exports/listings.csv').text

def test_durable_job_recovery_and_failure(monkeypatch):
    from app.db import Job
    from app.service import enqueue, poll_jobs
    import app.service as service
    with Session() as db:
        jid=enqueue(db,'nongjy'); assert enqueue(db,'nongjy')==jid;db.commit()
        job=db.get(Job,jid);job.state='running';job.lease_until='2000-01-01T00:00:00+00:00';db.commit()
    monkeypatch.setattr(service,'crawl',lambda sid: {'records':2})
    poll_jobs()
    with Session() as db:
        assert db.get(Job,jid).state=='complete'
        assert db.get(Job,jid).result['records']==2
        second=enqueue(db,'nongjy');db.commit()
    def fail(sid): raise SourceError('HTTP 403')
    monkeypatch.setattr(service,'crawl',fail);poll_jobs()
    with Session() as db: assert db.get(Job,second).state=='failed'

def test_sold_price_kind_does_not_become_starting_bid():
    f,_,_=nongjy_parse(sample().replace('起始价','成交价'),'https://www.nongjy.cn/web/propertyBid/detail/1')
    assert f['price_kind']=='sale'

def test_sort_tolerates_unknown_price_kind():
    with Session() as db:
        for i, html in enumerate([sample(), sample().replace('起始价','未声明金额性质')], 1):
            ingest(db,'nongjy',f'https://www.nongjy.cn/web/propertyBid/detail/{i}',html);db.commit()
    c=client_for('member')
    r=c.post('/api/v1/listings/search',json={'sort':'monthly'})
    assert r.status_code==200 and r.json()['total']==2
    assert {x['price_kind'] for x in r.json()['items']} == {'starting_bid', None}

def test_same_input_new_extraction_is_not_market_change(monkeypatch):
    import app.service as service
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
    parser=service.PARSERS['nongjy']
    def corrected(html,url):
        fields,evidence,text=parser(html,url)
        fields['area_m2']='61'
        return fields,evidence,text
    monkeypatch.setitem(service.PARSERS,'nongjy',corrected)
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
        events=list(db.scalars(select(Event).order_by(Event.id)))
        assert [e.kind for e in events]==['new','reprocessing']
