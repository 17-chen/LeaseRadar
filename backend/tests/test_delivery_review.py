from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy import select,func
from app.db import Session,User,Subscription,Outbox,Event,Version,Listing,EmailDelivery,SourceIncident,IncidentEmail,AuditAction,NotificationPreference
from app.incident_email import deliver_incidents
from app.email_delivery import deliver_email
from test_core import sample,client_for
from app.service import ingest,deliver_local

@pytest.fixture
def configured(monkeypatch):
    at=datetime.now(timezone.utc)-timedelta(seconds=1)
    with Session() as db:uid=db.scalar(select(User.id).where(User.username=='admin'))
    for k,v in {'EMAIL_ENABLED':'true','EMAIL_USER_ID':str(uid),'EMAIL_RECIPIENT':'synthetic@example.test','EMAIL_START_AT':at.isoformat(),'SMTP_HOST':'127.0.0.1','SMTP_FROM':'sender@example.test','SMTP_SECURITY':'local','SOURCE_ALERT_EMAIL_ENABLED':'true'}.items():monkeypatch.setenv(k,v)
    return at


def incident(at):
    with Session() as db:
        row=SourceIncident(source_id='nongjy',kind='source_error',message='synthetic HTTP 403',opened_at=at.isoformat());db.add(row);db.commit();return row.id


def receipt(state='dead_letter',attempts=3):
    with Session() as db:
        user=db.scalar(select(User).where(User.username=='admin'));db.add(Subscription(user_id=user.id,name='synthetic',filters={}));db.flush()
        ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample());db.commit()
    deliver_local()
    with Session() as db:
        notice=db.scalar(select(Outbox));r=EmailDelivery(outbox_id=notice.id,recipient='synthetic@example.test',state=state,attempts=attempts);db.add(r);db.commit();return r.id


def review_payload(state='dead_letter',action='retry',**extra):return {'expected_state':state,'action':action,'reason':'合成核验：已修复通道后处理记录',**extra}


def test_incident_open_recovery_and_repeat_are_distinct(configured):
    at=configured+timedelta(seconds=2);iid=incident(at);received=[]
    sender=lambda cfg,m:(received.append(m) or ('accepted',None))
    assert deliver_incidents(at,sender)==1 and deliver_incidents(at,sender)==0
    with Session() as db:r=db.get(SourceIncident,iid);r.state='resolved';r.resolved_at=(at+timedelta(minutes=1)).isoformat();db.commit()
    assert deliver_incidents(at+timedelta(minutes=1),sender)==1
    assert len(received)==2 and received[0]['Message-ID']!=received[1]['Message-ID']
    with Session() as db:assert db.scalar(select(func.count()).select_from(Outbox))==0


def test_alert_disabled_and_nonadmin_never_send(configured,monkeypatch):
    iid=incident(configured+timedelta(seconds=2));sent=[]
    monkeypatch.setenv('SOURCE_ALERT_EMAIL_ENABLED','false');assert deliver_incidents(sender=lambda *a:sent.append(1))==0
    monkeypatch.setenv('SOURCE_ALERT_EMAIL_ENABLED','true')
    with Session() as db:uid=db.scalar(select(User.id).where(User.username=='member'))
    monkeypatch.setenv('EMAIL_USER_ID',str(uid))
    with pytest.raises(ValueError):deliver_incidents(sender=lambda *a:sent.append(1))
    assert not sent


def test_stale_open_cancelled_and_old_history_not_backfilled(configured):
    incident(configured-timedelta(days=1));iid=incident(configured+timedelta(seconds=2))
    at=configured+timedelta(seconds=3)
    assert deliver_incidents(at,sender=lambda *a:('retry_wait','synthetic temporary'))==1
    with Session() as db:r=db.get(SourceIncident,iid);r.state='resolved';r.resolved_at=at.isoformat();db.commit()
    assert deliver_incidents(at+timedelta(minutes=2),sender=lambda *a:('accepted',None))==1
    with Session() as db:
        rows=list(db.scalars(select(IncidentEmail).order_by(IncidentEmail.id)))
        assert [r.state for r in rows]==['cancelled','accepted'] and len(rows)==2


def test_manual_deadletter_one_retry_preserves_attempts_and_audit(configured):
    identity=receipt();c=client_for('admin')
    assert c.post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload()).status_code==200
    assert deliver_email(sender=lambda *a:('retry_wait','synthetic temporary'))==1
    with Session() as db:
        row=db.get(EmailDelivery,identity);assert row.state=='dead_letter' and row.attempts==4
        assert db.scalar(select(AuditAction)).kind=='email_retry'


def test_ambiguous_not_blind_retry_but_provider_evidence_allows_one(configured):
    identity=receipt('ambiguous',1);c=client_for('admin')
    assert c.post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload('ambiguous','retry')).status_code==409
    assert c.post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload('ambiguous','confirm_unsent',receipt='')).status_code==409
    assert c.post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload('ambiguous','confirm_unsent',receipt='合成回执核验：服务商确认未接受该Message-ID')).status_code==200
    deliver_email(sender=lambda *a:('retry_wait','synthetic'))
    with Session() as db:assert db.get(EmailDelivery,identity).state=='dead_letter' and db.get(EmailDelivery,identity).attempts==2


def test_close_never_auto_resumes_and_confirm_accepted_never_resends(configured):
    identity=receipt('ambiguous',1);c=client_for('admin')
    assert c.post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload('ambiguous','close')).status_code==200
    received=[];assert deliver_email(sender=lambda *a:received.append(1))==0
    with Session() as db:assert db.get(EmailDelivery,identity).state=='closed'
    assert not received


def test_provider_acceptance_requires_time_and_permission(configured):
    identity=receipt('ambiguous',1);a=client_for('admin');m=client_for('member')
    payload=review_payload('ambiguous','confirm_accepted',receipt='合成服务商记录确认该邮件已接受',accepted_at=datetime.now(timezone.utc).isoformat())
    assert m.post(f'/api/v1/email-deliveries/{identity}/review',json=payload).status_code==403
    assert a.post(f'/api/v1/email-deliveries/{identity}/review',json={**payload,'accepted_at':None}).status_code==409
    assert a.post(f'/api/v1/email-deliveries/{identity}/review',json=payload).status_code==200
    assert a.post(f'/api/v1/email-deliveries/{identity}/review',json=payload).status_code==409
    assert deliver_email(sender=lambda *a:('accepted',None))==0


def test_recipient_change_blocks_replay(configured,monkeypatch):
    identity=receipt();monkeypatch.setenv('EMAIL_RECIPIENT','another@example.test')
    assert client_for('admin').post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload()).status_code==409


def test_incident_review_and_owner_history(configured):
    incident(configured+timedelta(seconds=2));deliver_incidents(configured+timedelta(seconds=3),sender=lambda *a:('dead_letter','synthetic'))
    a=client_for('admin');m=client_for('member');rows=a.get('/api/v1/incident-emails').json()['items']
    assert len(rows)==1 and m.get('/api/v1/incident-emails').status_code==403
    assert a.post(f"/api/v1/incident-emails/{rows[0]['id']}/review",json=review_payload()).status_code==200


def test_message_identity_saved_and_sender_change_blocks_retry(configured,monkeypatch):
    identity=receipt();c=client_for('admin');received=[]
    assert c.post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload()).status_code==200
    deliver_email(sender=lambda cfg,msg:(received.append(msg['Message-ID']) or ('dead_letter','synthetic')))
    with Session() as db:assert db.get(EmailDelivery,identity).message_id==received[0]
    assert c.get('/api/v1/email-deliveries/history').json()['items'][0]['message_id']==received[0]
    monkeypatch.setenv('SMTP_FROM','different@example.test')
    assert c.post(f'/api/v1/email-deliveries/{identity}/review',json=review_payload()).status_code==409


def test_alert_retry_exhaustion_and_unknown_lease(configured):
    at=configured+timedelta(seconds=2);incident(at)
    for n in range(3):deliver_incidents(at+timedelta(minutes=5*n),sender=lambda *a:('retry_wait','synthetic'))
    with Session() as db:
        row=db.scalar(select(IncidentEmail));assert row.state=='dead_letter' and row.attempts==3
        row.state='sending';row.lease_until=at.isoformat();row.token='old';db.commit()
    deliver_incidents(at+timedelta(minutes=20),sender=lambda *a:('accepted',None))
    with Session() as db:assert db.scalar(select(IncidentEmail)).state=='ambiguous'


def test_incidents_respect_quiet_and_end_does_not_claim_source_recovered(configured):
    at=configured+timedelta(seconds=2);iid=incident(at);received=[]
    with Session() as db:
        uid=db.scalar(select(User.id).where(User.username=='admin'))
        db.add(NotificationPreference(user_id=uid,timezone='UTC',quiet_start=(at-timedelta(hours=1)).strftime('%H:%M'),quiet_end=(at+timedelta(hours=1)).strftime('%H:%M')));db.commit()
    sender=lambda cfg,message:(received.append(message) or ('accepted',None))
    assert deliver_incidents(at,sender)==0
    assert deliver_incidents(at+timedelta(hours=2),sender)==1
    with Session() as db:r=db.get(SourceIncident,iid);r.state='resolved';r.resolved_at=(at+timedelta(hours=3)).isoformat();db.commit()
    assert deliver_incidents(at+timedelta(hours=3),sender)==1
    assert '现状须核验' in received[-1]['Subject']
