"""Admin-only source incident transport with separate opening/recovery identities."""
import os,secrets
from datetime import datetime,timedelta,timezone
from email.message import EmailMessage
from sqlalchemy import select,update,or_
from sqlalchemy.exc import IntegrityError
from .db import Session,User,SourceIncident,Source,IncidentEmail
from .email_delivery import settings,smtp_send
from .domain import aware_time
from .config import MODE


def configuration(db):
    if os.getenv('SOURCE_ALERT_EMAIL_ENABLED','false').lower()!='true':return None
    config=settings()
    if not config:return None
    user=db.get(User,config['user_id'])
    if not user or user.role!='admin':raise ValueError('来源告警接收用户必须是管理员')
    return config


def valid(db,row,config):
    incident=db.get(SourceIncident,row.incident_id)
    return bool(incident and row.user_id==config['user_id'] and row.recipient==config['recipient'] and (not row.sender_address or row.sender_address==config['sender']) and
        (incident.state=='open' if row.phase=='open' else incident.state=='resolved'))


def deliver_incidents(at=None,sender=smtp_send):
    fixed_at=at;at=at or datetime.now(timezone.utc)
    with Session() as db:
        config=configuration(db)
        if not config:return 0
        db.execute(update(IncidentEmail).where(IncidentEmail.state=='sending',IncidentEmail.lease_until<=at.isoformat()).values(state='ambiguous',token=None,error='Send lease expired; receipt unknown'))
        for incident in db.scalars(select(SourceIncident)):
            phase='open' if incident.state=='open' else 'resolved'
            occurred=aware_time(incident.opened_at if phase=='open' else incident.resolved_at)
            if not occurred or occurred<config['start']:continue
            if db.scalar(select(IncidentEmail.id).where(IncidentEmail.incident_id==incident.id,IncidentEmail.phase==phase)):continue
            try:
                with db.begin_nested():db.add(IncidentEmail(incident_id=incident.id,phase=phase,user_id=config['user_id'],recipient=config['recipient'],sender_address=config['sender'],created_at=at.isoformat()));db.flush()
            except IntegrityError:
                if not db.scalar(select(IncidentEmail.id).where(IncidentEmail.incident_id==incident.id,IncidentEmail.phase==phase)):raise
        ids=list(db.scalars(select(IncidentEmail.id).where(IncidentEmail.state.in_(['queued','retry_wait']),or_(IncidentEmail.retry_at.is_(None),IncidentEmail.retry_at<=at.isoformat())).order_by(IncidentEmail.id).limit(20)))
        db.commit()
    sent=0
    for identity in ids:
        at=fixed_at or datetime.now(timezone.utc);token=secrets.token_hex(16)
        with Session() as db:
            row=db.get(IncidentEmail,identity)
            if not valid(db,row,config):
                db.execute(update(IncidentEmail).where(IncidentEmail.id==identity,IncidentEmail.state.in_(['queued','retry_wait'])).values(state='cancelled'));db.commit();continue
            from .scheduling import quiet
            from .db import NotificationPreference
            if quiet(db.get(NotificationPreference,row.user_id),at):continue
            claimed=db.execute(update(IncidentEmail).where(IncidentEmail.id==identity,IncidentEmail.state.in_(['queued','retry_wait']),or_(IncidentEmail.retry_at.is_(None),IncidentEmail.retry_at<=at.isoformat())).values(state='sending',token=token,attempts=IncidentEmail.attempts+1,lease_until=(at+timedelta(minutes=5)).isoformat()))
            db.commit()
            if not claimed.rowcount:continue
            db.refresh(row)
            if not row.message_id:row.message_id=f'<leaseradar-incident-{row.id}@{config["sender"].split("@")[1]}>'
            if not row.sender_address:row.sender_address=config['sender']
            db.commit()
            incident=db.get(SourceIncident,row.incident_id);source=db.get(Source,incident.source_id)
            message=EmailMessage();message['From']=config['sender'];message['To']=row.recipient
            message['Subject']='LeaseRadar 来源异常' if row.phase=='open' else 'LeaseRadar 来源异常结束（现状须核验）'
            message['Message-ID']=row.message_id
            message.set_content(f'模式：{MODE}\n来源：{source.name}\n异常编号：{incident.id}\n阶段：{row.phase}\n'
                f'开始：{incident.opened_at}\n恢复：{incident.resolved_at or "尚未恢复"}\n原因：{incident.message}\n'
                f'最近成功观测：{source.last_success_at or "未知"}\n覆盖：{source.coverage or "未知"}\n'
                '异常恢复只表示该异常结束，不保证全站覆盖或来源持续正常。')
            state,error=sender(config,message)
            if state=='retry_wait' and (row.manual_retry or row.attempts>=3):state='dead_letter'
            db.execute(update(IncidentEmail).where(IncidentEmail.id==row.id,IncidentEmail.state=='sending',IncidentEmail.token==token).values(state=state,error=error,token=None,lease_until=None,retry_at=(at+timedelta(seconds=60*2**(row.attempts-1))).isoformat() if state=='retry_wait' else None,accepted_at=at.isoformat() if state=='accepted' else None))
            db.commit();sent+=1
    return sent
