"""All addresses and SMTP servers here are synthetic/local."""
from datetime import datetime, timedelta, timezone
import socketserver
import threading
import pytest
from sqlalchemy import select, func
from app.db import Session, User, Subscription, EmailDelivery, Outbox, Source
from app.service import ingest, deliver_local
from app.email_delivery import deliver_email, settings
from test_core import sample, client_for

@pytest.fixture
def configured(monkeypatch):
    at = datetime.now(timezone.utc)
    with Session() as db:
        user = db.scalar(select(User).where(User.username == 'member'))
        sub = Subscription(user_id=user.id, name='email test', filters={})
        db.add(sub); db.commit()
        ingest(db, 'nongjy', 'https://www.nongjy.cn/web/propertyBid/detail/1', sample()); db.commit()
        uid = user.id
    for key, value in {'EMAIL_ENABLED':'true', 'SMTP_FROM':'sender@example.test',
            'EMAIL_RECIPIENT':'recipient@example.test', 'EMAIL_USER_ID':str(uid),
            'EMAIL_START_AT':(at-timedelta(seconds=1)).isoformat(), 'SMTP_HOST':'127.0.0.1',
            'SMTP_SECURITY':'local', 'SMTP_PORT':'2525'}.items(): monkeypatch.setenv(key, value)
    return at

def test_disabled_does_not_queue(monkeypatch):
    monkeypatch.setenv('EMAIL_ENABLED', 'false')
    assert deliver_email() == 0

@pytest.mark.parametrize('key,value', [('EMAIL_START_AT','2026-01-01'),
    ('SMTP_HOST','mail.example.test'), ('EMAIL_RECIPIENT','a@example.test\r\nBcc: x@example.test')])
def test_invalid_configuration(configured, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError): settings()

def test_dedup_and_owner_receipts(configured):
    captured = []
    def send(config, message): captured.append(message); return 'accepted', None
    assert deliver_email(sender=send) == 1
    assert deliver_email(sender=send) == 0
    assert len(captured) == 1 and 'recipient@example.test' == captured[0]['To']
    assert len(client_for('member').get('/api/v1/email-deliveries').json()) == 1
    assert client_for('other').get('/api/v1/email-deliveries').json() == []
    assert client_for('member').get('/api/v1/source-alerts').status_code == 403

def test_retry_dead_letter(configured):
    fail = lambda c,m: ('retry_wait', 'SMTP 451')
    assert deliver_email(sender=fail) == 1
    assert deliver_email(sender=fail) == 0
    assert deliver_email(configured + timedelta(minutes=2), sender=fail) == 1
    assert deliver_email(configured + timedelta(minutes=5), sender=fail) == 1
    with Session() as db:
        row=db.scalar(select(EmailDelivery)); assert (row.state,row.attempts)==('dead_letter',3)

def test_ambiguous_no_auto_retry_and_paused_cancellation(configured):
    deliver_email(sender=lambda c,m: ('ambiguous','unknown'))
    assert deliver_email(configured+timedelta(days=1),sender=lambda c,m:pytest.fail('must not resend'))==0
    with Session() as db:
        row=db.scalar(select(EmailDelivery)); row.state='retry_wait'; row.retry_at=None
        db.scalar(select(Subscription)).enabled=False; db.commit()
    deliver_email(sender=lambda c,m:pytest.fail('paused'))
    with Session() as db: assert db.scalar(select(EmailDelivery)).state=='cancelled'

def test_expired_lease_is_ambiguous(configured):
    deliver_email(sender=lambda c,m: ('retry_wait','temporary'))
    with Session() as db:
        row=db.scalar(select(EmailDelivery)); row.state='sending'; row.lease_until=configured.isoformat(); row.token='old'; db.commit()
    deliver_email(configured+timedelta(minutes=1),sender=lambda c,m:pytest.fail('unknown receipt'))
    with Session() as db: assert db.scalar(select(EmailDelivery)).state=='ambiguous'

def test_start_time_excludes_history(configured, monkeypatch):
    monkeypatch.setenv('EMAIL_START_AT',(configured+timedelta(days=1)).isoformat())
    assert deliver_email(sender=lambda c,m:pytest.fail('history'))==0

def test_local_smtp_acceptance(configured, monkeypatch):
    received=[]
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.wfile.write(b'220 local test\r\n')
            while line:=self.rfile.readline():
                command=line.split(b' ')[0].strip().upper()
                if command==b'DATA':
                    self.wfile.write(b'354 send data\r\n')
                    content=[]
                    while (line:=self.rfile.readline()) and line!=b'.\r\n': content.append(line)
                    received.append(b''.join(content)); self.wfile.write(b'250 accepted\r\n')
                else: self.wfile.write(b'250 OK\r\n')
    with socketserver.TCPServer(('127.0.0.1',0),Handler) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        monkeypatch.setenv('SMTP_PORT',str(server.server_address[1]))
        try: assert deliver_email()==1
        finally: server.shutdown();thread.join()
    assert len(received)==1 and b'Message-ID: <leaseradar-' in received[0]
    with Session() as db: assert db.scalar(select(EmailDelivery)).state=='accepted'

def test_source_incident_resolves(configured):
    with Session() as db:
        source=db.get(Source,'nongjy');source.status='blocked';source.error='HTTP 403'; db.commit()
    admin=client_for('admin')
    assert admin.get('/api/v1/source-alerts').json()[0]['id']=='source:nongjy'
    with Session() as db: db.get(Source,'nongjy').error=None;db.commit()
    assert admin.get('/api/v1/source-alerts').json()==[]

@pytest.mark.parametrize('phase,code,expected', [('mail',451,'retry_wait'),('rcpt',550,'dead_letter'),
    ('data',451,'retry_wait'),('timeout_before',None,'retry_wait'),('timeout_after',None,'ambiguous')])
def test_smtp_failure_boundary(configured, monkeypatch, phase, code, expected):
    from app.email_delivery import smtp_send
    from email.message import EmailMessage
    class FakeSMTP:
        def __init__(self,*a,**kw):
            if phase=='timeout_before': raise TimeoutError()
        def ehlo(self): pass
        def mail(self,address): return (code if phase=='mail' else 250),b'ignored response'
        def rcpt(self,address): return (code if phase=='rcpt' else 250),b'ignored response'
        def data(self,body):
            if phase=='timeout_after': raise TimeoutError()
            return (code if phase=='data' else 250),b'ignored response'
        def close(self): pass
    monkeypatch.setattr('app.email_delivery.smtplib.SMTP',FakeSMTP)
    message=EmailMessage();message.set_content('synthetic')
    assert smtp_send(settings(),message)[0]==expected

def test_invalidated_reminder_never_sent(configured):
    from app.notifications import generate_deadline_reminders
    from app.db import Version, Listing, SourceRecord
    with Session() as db:
        listing=db.scalar(select(Listing));v=db.get(Version,listing.current_version_id)
        v.fields={**v.fields,'registration_deadline':(configured+timedelta(hours=10)).isoformat()}
        db.scalar(select(SourceRecord)).last_checked_at=configured.isoformat();db.commit()
    generate_deadline_reminders(configured)
    with Session() as db:
        db.scalar(select(Outbox).where(Outbox.event_id.is_not(None))).state='cancelled'
        db.get(Version,listing.current_version_id).fields={**v.fields,'status':'closed'};db.commit()
    assert deliver_email(configured,sender=lambda c,m:pytest.fail('closed reminder'))==0

def test_old_sender_cannot_overwrite_unknown_receipt(configured):
    def expired_sender(config,message):
        with Session() as db:
            row=db.scalar(select(EmailDelivery));row.state='ambiguous';row.token=None;db.commit()
        return 'accepted',None
    deliver_email(sender=expired_sender)
    with Session() as db:
        row=db.scalar(select(EmailDelivery));assert row.state=='ambiguous' and row.accepted_at is None
