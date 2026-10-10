"""Synthetic lifecycle scenarios; never send notices to real recipients."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.db import Session, Source, SourceRecord, Listing, Version, Subscription, User, Outbox, Event, Followup, CrawlRun, DeadlineReminder
from app.collectors import SourceError
from app.notifications import generate_deadline_reminders
from app.service import ingest, detail_targets, refresh_details, deliver_local
from test_core import sample, client_for

AT = lambda: datetime.now(timezone.utc).replace(microsecond=0)

def html_deadline(at, hours=50, price='120000'):
    cutoff=(at+timedelta(hours=hours)).astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
    return sample(price).replace('2099-10-16 16:00:00',cutoff)

def setup_reminder(at, filters=None, unknown_policy='review_digest', hours=None):
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',html_deadline(at),attachment_cache={})
        record=db.scalar(select(SourceRecord));record.last_checked_at=(at-timedelta(minutes=1)).isoformat()
        user=db.scalar(select(User).where(User.username=='member'))
        sub=Subscription(user_id=user.id,name='synthetic',filters=filters or {},unknown_policy=unknown_policy,
                         reminder_hours=hours if hours is not None else [72,24])
        db.add(sub);db.commit()
        return sub.id, record.listing_id

def test_detail_selection_handles_active_watched_and_stopped_history():
    at=AT()
    with Session() as db:
        user=db.scalar(select(User).where(User.username=='member'))
        for i in range(1,6):
            body=html_deadline(at,50 if i==1 else -100)
            ingest(db,'nongjy',f'https://www.nongjy.cn/web/propertyBid/detail/{i}',body,attachment_cache={})
        for record in db.scalars(select(SourceRecord)):
            record.last_checked_at=(at-timedelta(days=2)).isoformat()
            if record.record_id in ('3','4'):
                db.add(Followup(user_id=user.id,listing_id=record.listing_id,favorite=True,
                                status='放弃' if record.record_id=='4' else '已查看'))
        # Recent verification must not be fetched again.
        db.scalar(select(SourceRecord).where(SourceRecord.record_id=='5')).last_checked_at=at.isoformat()
        db.commit()
        assert [url.rsplit('/',1)[-1] for _,url in detail_targets(db,'nongjy',at)]==['1','3']

def test_partial_detail_failure_keeps_success_and_resumes_remaining(monkeypatch):
    import app.service as service
    at=AT()
    with Session() as db:
        for i in (1,2):
            ingest(db,'nongjy',f'https://www.nongjy.cn/web/propertyBid/detail/{i}',html_deadline(at),attachment_cache={})
        for record in db.scalars(select(SourceRecord)):
            record.last_checked_at=(at-timedelta(hours=2)).isoformat()
        user=db.scalar(select(User).where(User.username=='member'))
        db.add(Subscription(user_id=user.id,name='open only',filters={'status':'open'}));db.commit()
    visited=[]
    def fetch(url):
        visited.append(url)
        if url.endswith('/2'): raise SourceError('temporary',retryable=True)
        return html_deadline(at).replace('报名交保证金','报名已截止')
    monkeypatch.setattr(service,'fetch',fetch)
    with pytest.raises(SourceError): refresh_details('nongjy',delay=0)
    with Session() as db:
        assert db.scalar(select(CrawlRun)).stored==1
        assert db.get(Source,'nongjy').lease_until is None
        row=db.scalar(select(Outbox))
        assert row.payload['notice_class']=='status_update' and row.payload['match']['verdict']=='fail'
        assert row.payload['changes'][0]=={'field':'status','before':'open','after':'closed'}
    monkeypatch.setattr(service,'fetch',lambda url: visited.append(url) or html_deadline(at))
    assert refresh_details('nongjy',delay=0)['checked']==1
    assert visited[-1].endswith('/2')

def test_detail_lease_prevents_overlapping_fetch(monkeypatch):
    import app.service as service
    with Session() as db:
        db.get(Source,'nongjy').lease_until=(AT()+timedelta(hours=1)).isoformat();db.commit()
    monkeypatch.setattr(service,'fetch',lambda url: pytest.fail('must not fetch while leased'))
    with pytest.raises(SourceError,match='已运行'): refresh_details('nongjy',delay=0)
    with Session() as db: assert db.scalar(select(func.count()).select_from(CrawlRun))==0

def test_empty_detail_check_does_not_claim_fresh_source_data(monkeypatch):
    import app.service as service
    monkeypatch.setattr(service,'fetch',lambda url: pytest.fail('empty selection must not fetch'))
    assert refresh_details('wzpt',delay=0)['checked']==0
    with Session() as db:
        source=db.get(Source,'wzpt')
        assert source.last_success_at is None and source.status=='pending_validation'


def test_deadline_reminders_deduplicate_across_versions_and_windows():
    at=AT();setup_reminder(at)
    assert generate_deadline_reminders(at)==1
    assert generate_deadline_reminders(at)==0
    deliver_local()
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',html_deadline(at,price='130000'),attachment_cache={});db.commit()
    assert generate_deadline_reminders(at)==0
    later=at+timedelta(hours=30)
    with Session() as db:
        db.scalar(select(SourceRecord)).last_checked_at=(later-timedelta(minutes=1)).isoformat();db.commit()
    assert generate_deadline_reminders(later)==1
    assert generate_deadline_reminders(later)==0
    with Session() as db:
        reminders=list(db.scalars(select(DeadlineReminder).order_by(DeadlineReminder.id)))
        assert [r.lead_hours for r in reminders]==[72,24]
        first=db.scalar(select(Outbox).where(Outbox.reminder_id==reminders[0].id))
        assert first.state=='accepted'  # Earlier delivered window remains valid history.


def test_worker_catchup_generates_only_nearest_deadline_window():
    at=AT();setup_reminder(at)
    later=at+timedelta(hours=40)
    with Session() as db:
        db.scalar(select(SourceRecord)).last_checked_at=(later-timedelta(minutes=1)).isoformat();db.commit()
    assert generate_deadline_reminders(later)==1
    with Session() as db: assert db.scalar(select(DeadlineReminder)).lead_hours==24


def test_extension_cancels_old_reminder_and_creates_new_deadline_identity():
    at=AT();setup_reminder(at);assert generate_deadline_reminders(at)==1
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',html_deadline(at,100),attachment_cache={});db.commit()
        assert db.scalar(select(Outbox).where(Outbox.reminder_id.is_not(None))).state=='cancelled'
    assert generate_deadline_reminders(at)==0
    later=at+timedelta(hours=50)
    with Session() as db:
        db.scalar(select(SourceRecord)).last_checked_at=(later-timedelta(minutes=1)).isoformat();db.commit()
    assert generate_deadline_reminders(later)==1
    with Session() as db: assert db.scalar(select(func.count()).select_from(DeadlineReminder))==2

@pytest.mark.parametrize('reason',['closed','stopped','paused','expired','hours_removed'])
def test_obsolete_reminders_cancel_before_acceptance(reason):
    at=AT();sub_id,listing_id=setup_reminder(at);assert generate_deadline_reminders(at)==1
    with Session() as db:
        sub=db.get(Subscription,sub_id);version=db.get(Version,db.get(Listing,listing_id).current_version_id)
        if reason=='closed': version.fields={**version.fields,'status':'closed'}
        if reason=='expired': version.fields={**version.fields,'registration_deadline':(at-timedelta(hours=1)).isoformat()}
        if reason=='paused': sub.enabled=False
        if reason=='hours_removed': sub.reminder_hours=[]
        if reason=='stopped': db.add(Followup(user_id=sub.user_id,listing_id=listing_id,status='放弃'))
        db.commit()
    deliver_local()
    with Session() as db: assert db.scalar(select(Outbox).where(Outbox.reminder_id.is_not(None))).state=='cancelled'

@pytest.mark.parametrize('case',['unknown_excluded','old_observation','auction_only','date_only','naive_time'])
def test_unsafe_or_stale_deadline_is_not_a_reminder(case):
    at=AT();_,listing_id=setup_reminder(at,filters={'operation':'coffee_beverage'} if case=='unknown_excluded' else {},unknown_policy='exclude')
    with Session() as db:
        version=db.get(Version,db.get(Listing,listing_id).current_version_id)
        if case=='old_observation': db.scalar(select(SourceRecord)).last_checked_at=(at-timedelta(hours=25)).isoformat()
        if case=='auction_only': version.fields={**version.fields,'registration_deadline':None,'auction_deadline':(at+timedelta(hours=24)).isoformat()}
        if case=='date_only': version.fields={**version.fields,'registration_deadline':None,'disclosure_deadline':(at+timedelta(days=1)).date().isoformat()}
        if case=='naive_time': version.fields={**version.fields,'registration_deadline':(at+timedelta(hours=24)).replace(tzinfo=None).isoformat()}
        db.commit()
    assert generate_deadline_reminders(at)==0


def test_reminder_configuration_validation_and_ownership():
    c=client_for('member');other=client_for('other')
    for invalid in ([0],[169],[24,24],[72,48,24,1],[True],[1.5],['24']):
        assert c.post('/api/v1/subscriptions',json={'name':'invalid','reminder_hours':invalid}).status_code==422
    sid=c.post('/api/v1/subscriptions',json={'name':'custom','reminder_hours':[12,48]}).json()['id']
    assert c.get('/api/v1/subscriptions').json()[0]['reminder_hours']==[48,12]
    assert other.patch(f'/api/v1/subscriptions/{sid}',json={'name':'stolen','reminder_hours':[]}).status_code==404
    assert c.patch(f'/api/v1/subscriptions/{sid}',json={'name':'disabled','reminder_hours':[]}).status_code==200


def test_reminder_outbox_origin_constraint_and_recipient_isolation():
    at=AT();sub_id,_=setup_reminder(at);generate_deadline_reminders(at)
    c=client_for('member');other=client_for('other')
    notice=c.get('/api/v1/notifications').json()[0]
    assert notice['kind']=='registration_reminder'
    assert other.get('/api/v1/notifications').json()==[]
    assert other.patch(f"/api/v1/notifications/{notice['id']}").status_code==404
    with Session() as db:
        db.add(Outbox(subscription_id=sub_id,payload={}))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()


def test_details_api_remains_admin_only():
    assert client_for('member').post('/api/v1/sources/nongjy/runs?kind=details').status_code==403
    c=client_for('admin');jid=c.post('/api/v1/sources/nongjy/runs?kind=details').json()['job_id']
    assert c.get(f'/api/v1/jobs/{jid}').json()['kind']=='details'

def test_pending_reminder_does_not_deliver_after_observation_becomes_stale():
    at=AT();setup_reminder(at);generate_deadline_reminders(at)
    with Session() as db:
        db.scalar(select(SourceRecord)).last_checked_at=(at-timedelta(hours=25)).isoformat();db.commit()
    deliver_local()
    with Session() as db: assert db.scalar(select(Outbox)).state=='cancelled'

def test_unknown_price_basis_change_is_not_declared_a_confirmed_drop():
    at=AT()
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',html_deadline(at),attachment_cache={});db.commit()
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',html_deadline(at,price='100000'),attachment_cache={});db.commit()
        assert list(db.scalars(select(Event.kind).order_by(Event.id)))==['new','changed']

def test_source_api_does_not_claim_different_pending_job_as_details():
    c=client_for('admin')
    jid=c.post('/api/v1/sources/nongjy/runs').json()['job_id']
    assert c.post('/api/v1/sources/nongjy/runs?kind=details').status_code==409
    assert c.post('/api/v1/sources/nongjy/runs').json()['job_id']==jid

def test_paused_subscription_cancels_pending_business_notice():
    at=AT();sub_id,_=setup_reminder(at)
    with Session() as db:
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',html_deadline(at,price='130000'),attachment_cache={});db.commit()
        db.get(Subscription,sub_id).enabled=False;db.commit()
    deliver_local()
    with Session() as db: assert db.scalar(select(Outbox)).state=='cancelled'

def test_concurrent_reminder_cycles_have_one_internal_notification():
    from concurrent.futures import ThreadPoolExecutor
    at=AT();setup_reminder(at)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results=list(workers.map(lambda _: generate_deadline_reminders(at),range(2)))
    assert sum(results)==1
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(DeadlineReminder))==1
        assert db.scalar(select(func.count()).select_from(Outbox).where(Outbox.reminder_id.is_not(None)))==1

@pytest.mark.parametrize('accepted',[False,True])
def test_resuming_subscription_reuses_unsent_reminder_but_does_not_resend_accepted(accepted):
    from app.notifications import cancel_invalid_reminders
    at=AT();sub_id,_=setup_reminder(at);generate_deadline_reminders(at)
    if accepted: deliver_local()
    with Session() as db:
        db.get(Subscription,sub_id).enabled=False;cancel_invalid_reminders(db,at);db.commit()
        assert db.scalar(select(Outbox)).payload['accepted_before_cancellation'] is accepted
        db.get(Subscription,sub_id).enabled=True;db.commit()
    assert generate_deadline_reminders(at)==(0 if accepted else 1)
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Outbox))==1
        assert db.scalar(select(Outbox)).state==('cancelled' if accepted else 'queued')
