"""Opt-in SMTP transport. Acceptance means SMTP acceptance, never inbox delivery."""
import os
import re
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError
from .db import Session, Outbox, Subscription, EmailDelivery
from .notifications import aware_time, reminder_valid
from .db import DeadlineReminder


def settings():
    if os.getenv('EMAIL_ENABLED', 'false').lower() != 'true': return None
    sender, recipient = os.getenv('SMTP_FROM', ''), os.getenv('EMAIL_RECIPIENT', '')
    pattern = r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+'
    if not all(re.fullmatch(pattern, address) for address in (sender, recipient)):
        raise ValueError('邮件地址配置无效')
    start = aware_time(os.getenv('EMAIL_START_AT'))
    if not start: raise ValueError('EMAIL_START_AT必须是带时区时间，防止补发历史消息')
    user_id = int(os.getenv('EMAIL_USER_ID', '0'))
    host = os.getenv('SMTP_HOST', '')
    security = os.getenv('SMTP_SECURITY', 'starttls')
    if not host or user_id < 1 or security not in ('starttls', 'ssl', 'local'):
        raise ValueError('邮件通道配置不完整')
    if security == 'local' and host not in ('127.0.0.1', '::1'):
        raise ValueError('明文SMTP仅允许本地测试接收端')
    port = int(os.getenv('SMTP_PORT', '587'))
    if not 1 <= port <= 65535: raise ValueError('SMTP端口必须为1–65535')
    return dict(sender=sender, recipient=recipient, start=start, user_id=user_id, host=host,
                security=security, port=port)


def eligible(db, notice, at):
    sub = db.get(Subscription, notice.subscription_id)
    return bool(sub and sub.enabled and notice.state in ('queued', 'accepted') and
        (not notice.reminder_id or reminder_valid(db, db.get(DeadlineReminder, notice.reminder_id), at)))


def smtp_send(config, message):
    client = None
    data_started = False
    try:
        cls = smtplib.SMTP_SSL if config['security'] == 'ssl' else smtplib.SMTP
        kwargs = {'context': ssl.create_default_context()} if config['security'] == 'ssl' else {}
        client = cls(config['host'], config['port'], timeout=15, **kwargs)
        client.ehlo()
        if config['security'] == 'starttls':
            client.starttls(context=ssl.create_default_context()); client.ehlo()
        if os.getenv('SMTP_USERNAME'):
            client.login(os.environ['SMTP_USERNAME'], os.getenv('SMTP_PASSWORD', ''))
        for command, address in ((client.mail, config['sender']), (client.rcpt, config['recipient'])):
            code, _ = command(address)
            if not 200 <= code < 300: return ('retry_wait' if 400 <= code < 500 else 'dead_letter'), f'SMTP {code}'
        data_started = True
        code, _ = client.data(message.as_bytes())
        if code == 250: return 'accepted', None
        return ('retry_wait' if 400 <= code < 500 else 'dead_letter'), f'SMTP {code}'
    except smtplib.SMTPResponseException as exc:
        return ('retry_wait' if 400 <= exc.smtp_code < 500 else 'dead_letter'), f'SMTP {exc.smtp_code}'
    except (OSError, smtplib.SMTPException):
        return ('ambiguous' if data_started else 'retry_wait'), 'SMTP connection failed; response unavailable'
    finally:
        if client:
            # close, not quit: a lost QUIT response must not invalidate DATA acceptance.
            client.close()


def deliver_email(at=None, sender=smtp_send):
    config = settings()
    if not config: return 0
    fixed_at = at
    at = at or datetime.now(timezone.utc)
    with Session() as db:
        # An expired send lease may have crossed the SMTP acceptance boundary.
        db.execute(update(EmailDelivery).where(EmailDelivery.state == 'sending',
            EmailDelivery.lease_until <= at.isoformat()).values(state='ambiguous', token=None,
                error='Send lease expired; receipt unknown'))
        notices = db.scalars(select(Outbox).join(Subscription).where(
            Subscription.user_id == config['user_id'], Outbox.channel == 'in_app',
            Outbox.created_at >= config['start'].isoformat()))
        for notice in notices:
            if not eligible(db, notice, at): continue
            existing = db.scalar(select(EmailDelivery).where(EmailDelivery.outbox_id == notice.id))
            if existing:
                # Only cancelled, known-unsent records may resume; accepted/ambiguous never do.
                if existing.state == 'cancelled' and existing.recipient == config['recipient'] and existing.accepted_at is None:
                    db.execute(update(EmailDelivery).where(EmailDelivery.id == existing.id,
                        EmailDelivery.state == 'cancelled').values(state='queued', retry_at=None, error=None))
                continue
            try:
                with db.begin_nested():
                    db.add(EmailDelivery(outbox_id=notice.id, recipient=config['recipient'])); db.flush()
            except IntegrityError:
                if not db.scalar(select(EmailDelivery.id).where(EmailDelivery.outbox_id == notice.id)): raise
        db.commit()
        ids = list(db.scalars(select(EmailDelivery.id).where(EmailDelivery.state.in_(['queued', 'retry_wait']),
            or_(EmailDelivery.retry_at.is_(None), EmailDelivery.retry_at <= at.isoformat()))
            .order_by(EmailDelivery.id).limit(20)))
    sent = 0
    for identity in ids:
        at = fixed_at or datetime.now(timezone.utc)
        token = secrets.token_hex(16)
        with Session() as db:
            row = db.get(EmailDelivery, identity)
            notice = db.get(Outbox, row.outbox_id)
            sub = db.get(Subscription, notice.subscription_id)
            if row.retry_at and aware_time(row.retry_at) > at: continue
            # Destination changes never redirect a previously queued message.
            if sub.user_id != config['user_id'] or row.recipient != config['recipient'] or not eligible(db, notice, at):
                db.execute(update(EmailDelivery).where(EmailDelivery.id == identity,
                    EmailDelivery.state.in_(['queued', 'retry_wait'])).values(state='cancelled')); db.commit(); continue
            claimed = db.execute(update(EmailDelivery).where(EmailDelivery.id == identity,
                EmailDelivery.state.in_(['queued', 'retry_wait']),
                or_(EmailDelivery.retry_at.is_(None), EmailDelivery.retry_at <= at.isoformat())).values(state='sending', token=token,
                    lease_until=(at + timedelta(minutes=5)).isoformat(), attempts=EmailDelivery.attempts + 1))
            db.commit()
            if not claimed.rowcount: continue
            row = db.get(EmailDelivery, identity); db.refresh(row)
            payload = notice.payload
            message = EmailMessage()
            message['From'] = config['sender']; message['To'] = row.recipient
            message['Subject'] = 'LeaseRadar 公告提醒'
            message['Message-ID'] = f'<leaseradar-{identity}@{config["sender"].split("@")[1]}>'
            message.set_content(f"模式：{payload.get('mode')}\n{payload.get('title', '')}\n"
                f"类型：{payload.get('notice_class')}\n匹配：{payload.get('match', {}).get('verdict', 'unknown')}\n"
                f"报名截止：{payload.get('registration_deadline') or '未知'}\n"
                f"来源：{payload.get('source_url', '')}\n请核验公告原文和未确认条件。")
            state, error = sender(config, message)
            if state == 'retry_wait' and row.attempts >= 3: state = 'dead_letter'
            db.execute(update(EmailDelivery).where(EmailDelivery.id == identity,
                EmailDelivery.state == 'sending', EmailDelivery.token == token).values(
                    state=state, error=error, token=None, lease_until=None,
                    retry_at=(at + timedelta(seconds=60 * 2 ** (row.attempts - 1))).isoformat() if state == 'retry_wait' else None,
                    accepted_at=at.isoformat() if state == 'accepted' else None))
            db.commit(); sent += 1
    return sent
