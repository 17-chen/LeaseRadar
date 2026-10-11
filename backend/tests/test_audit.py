"""Regression cases discovered by the full code and state audit."""
from datetime import datetime, timezone, timedelta
import ssl
import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from app.domain import match
from app.collectors import wzpt_parse, nongjy_parse, SourceError
from app.db import Session, Listing, SourceRecord, Version, RawDocument, Event, Subscription, User, Outbox, EmailDelivery
from app.service import ingest
from test_core import sample, client_for
from test_email import configured

AT=datetime(2026,10,11,tzinfo=timezone.utc)
WZ='https://www.wzpt.edu.cn/2026/0107/c739771a3318095/page.htm'
def wzhtml(title='校外公寓房屋租赁'):
    return f'<html><title>{title}</title><div class="wp_articlecontent"><a href="https://www.zjpse.com/prjs/lease/detail/235950.html">详情链接</a></div></html>'

@pytest.mark.parametrize('deadline',['2099-01-01T00:00:00','bad-time','2099-01-01'])
def test_bad_deadline_is_unknown_not_crash(deadline):
    assert match({'registration_deadline':deadline},{'registration_open':True},AT)['verdict']=='unknown'

def test_open_selector_excludes_expired_entry():
    assert match({'status':'open','registration_deadline':'2026-10-10T16:00:00+08:00'},{'status':'open'},AT)['verdict']=='fail'

def test_disclosure_uses_china_calendar_date():
    at=datetime(2026,10,11,18,tzinfo=timezone.utc)
    assert match({'disclosure_deadline':'2026-10-11'},{'registration_open':True},at)['verdict']=='fail'

def test_school_publisher_does_not_imply_campus_or_price():
    fields,evidence,_=wzpt_parse(wzhtml(),WZ)
    assert fields['environment'] is None and 'environment' not in evidence
    assert fields['price_kind'] is None and fields.get('raw_amount') is None
    assert match(fields,{'environment':'campus'})['verdict']=='unknown'

def test_unlabeled_nongjy_price_is_unknown():
    fields,_,_=nongjy_parse(sample().replace('起始价','金额'), 'https://www.nongjy.cn/web/propertyBid/detail/1')
    assert fields['price_kind'] is None

def test_wzpt_distinct_articles_do_not_overwrite():
    with Session() as db:
        first,_=ingest(db,'wzpt',WZ,wzhtml('合成甲'))
        second,_=ingest(db,'wzpt',WZ.replace('3318095','3318096'),wzhtml('合成乙'))
        db.commit()
        assert first!=second
        assert set(db.scalars(select(SourceRecord.record_id)))=={'3318095','3318096'}
        assert db.scalar(select(func.count()).select_from(Listing))==2

def test_legacy_wzpt_identity_and_offline_reparse_preserve_observation():
    past='2026-10-10T00:00:00+00:00'
    with Session() as db:
        lid,_=ingest(db,'wzpt',WZ,wzhtml(),observed_at=past);db.commit()
        db.scalar(select(SourceRecord)).record_id='page.htm';db.commit()
        same,changed=ingest(db,'wzpt',WZ,wzhtml(),observed_at=past);db.commit()
        assert same==lid and not changed
        record=db.scalar(select(SourceRecord))
        assert record.record_id=='3318095' and record.last_checked_at==past
        assert set(db.scalars(select(RawDocument.fetched_at)))=={past}

def test_ingest_rejects_mismatched_source_and_naive_observation():
    with Session() as db:
        with pytest.raises(SourceError): ingest(db,'nongjy',WZ,sample())
        with pytest.raises(ValueError): ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample(),observed_at='2026-10-10')

def test_sqlite_foreign_keys_are_enforced():
    with Session() as db:
        assert db.execute(text('PRAGMA foreign_keys')).scalar()==1
        db.add(EmailDelivery(outbox_id=999,recipient='synthetic@example.test'))
        with pytest.raises(IntegrityError): db.commit()

def test_smtp_ssl_verifies_certificate(configured,monkeypatch):
    from app.email_delivery import smtp_send,settings
    from email.message import EmailMessage
    monkeypatch.setenv('SMTP_SECURITY','ssl')
    checked=[]
    class VerifiedSMTP:
        def __init__(self,*args,**kwargs):
            context=kwargs['context']
            checked.append(context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname)
        def ehlo(self): pass
        def mail(self,recipient): return 250,b'OK'
        def rcpt(self,recipient): return 250,b'OK'
        def data(self,body): return 250,b'OK'
        def close(self): pass
    monkeypatch.setattr('app.email_delivery.smtplib.SMTP_SSL',VerifiedSMTP)
    message=EmailMessage();message.set_content('synthetic')
    assert smtp_send(settings(),message)[0]=='accepted' and checked==[True]

def test_future_retry_rows_do_not_starve_due_mail(configured):
    from app.email_delivery import deliver_email
    deliver_email(sender=lambda c,m:('retry_wait','synthetic'))
    with Session() as db:
        first=db.scalar(select(EmailDelivery));first.retry_at=(configured+timedelta(days=1)).isoformat()
        notice=db.scalar(select(Outbox));subid=notice.subscription_id
        for i in range(2,23):
            ingest(db,'nongjy',f'https://www.nongjy.cn/web/propertyBid/detail/{i}',sample());db.flush()
            n=db.scalar(select(Outbox).order_by(Outbox.id.desc()))
            db.add(EmailDelivery(outbox_id=n.id,recipient='recipient@example.test',state='retry_wait',
                retry_at=(configured+timedelta(days=1)).isoformat() if i<22 else None))
        db.commit()
    assert deliver_email(sender=lambda c,m:('accepted',None))==1

def test_resuming_paused_unsent_email_reuses_identity(configured):
    from app.email_delivery import deliver_email
    deliver_email(sender=lambda c,m:('retry_wait','synthetic'))
    with Session() as db:
        db.scalar(select(Subscription)).enabled=False
        db.scalar(select(EmailDelivery)).retry_at=None;db.commit()
    deliver_email(sender=lambda c,m:pytest.fail('paused'))
    with Session() as db:
        assert db.scalar(select(EmailDelivery)).state=='cancelled'
        db.scalar(select(Subscription)).enabled=True;db.commit()
    assert deliver_email(sender=lambda c,m:('accepted',None))==1
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(EmailDelivery))==1
        assert db.scalar(select(EmailDelivery)).state=='accepted'

def test_free_amount_survives_csv():
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample('0'));db.commit()
    import csv,io
    records=list(csv.DictReader(io.StringIO(client_for('member').get('/api/v1/exports/listings.csv').text.lstrip('\ufeff'))))
    assert records[0]['raw_amount']=='0'

def test_closed_selector_includes_elapsed_registration():
    assert match({'status':'open','registration_deadline':'2026-10-10T16:00:00+08:00'}, {'status':'closed'},AT)['verdict']=='pass'

def test_auth_responses_are_not_cached():
    client=client_for('member')
    assert client.get('/api/v1/auth/me').headers['cache-control']=='no-store'
    assert client.get('/').headers['cache-control']=='no-cache'
    assert client.get('/static/app.js').headers['cache-control']=='no-cache'

def test_new_snapshots_have_portable_relative_path():
    from app.config import DATA
    from pathlib import Path
    import hashlib
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
        raw=db.scalar(select(RawDocument))
        assert not Path(raw.snapshot_path).is_absolute()
        assert hashlib.sha256((DATA/raw.snapshot_path).read_bytes()).hexdigest()==raw.sha256

@pytest.mark.parametrize('area,expected',[('约1,234.50㎡','1234.50'),('1宗，约120㎡','120'),('30㎡和60㎡',None)])
def test_area_is_bound_to_unit_not_first_number(area,expected):
    f,_,_=nongjy_parse(sample().replace('约60㎡',area),'https://www.nongjy.cn/web/propertyBid/detail/1')
    assert f['area_m2']==expected

def test_currency_unit_is_not_lost():
    html=sample('8.35').replace('</span>元','</span>万元').replace('<div class="signupButton">','<div><span class="cont-info-left-bt">保证金：</span>2万元</div><div class="signupButton">')
    f,_,_=nongjy_parse(html,'https://www.nongjy.cn/web/propertyBid/detail/1')
    assert f['raw_amount']=='83500.00' and f['deposit']=='20000'

@pytest.mark.parametrize('value,expected',[('浙江省温州市龙湾区永中街道',('温州市','龙湾区')),('温州市鹿城区里某社区',('温州市','鹿城区'))])
def test_geography_does_not_include_province_or_community(value,expected):
    from app.collectors import location_parts
    assert location_parts(value)==expected

@pytest.mark.parametrize('value,expected',[('温州经济开发区沙城街道', (None,None)),('山东省青岛市市北区测试路',('青岛市','市北区'))])
def test_development_zone_is_not_administrative_district(value,expected):
    from app.collectors import location_parts
    assert location_parts(value)==expected
