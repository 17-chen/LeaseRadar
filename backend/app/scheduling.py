"""Opt-in local-time scheduling; no message leaves the transactional outbox."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, update
from .db import Session, Subscription, Outbox, NotificationPreference, Digest, DigestItem, Source
from .domain import aware_time
from .notifications import cancel_invalid_reminders


def quiet(pref, at):
    if not pref or not pref.quiet_start: return False
    clock = at.astimezone(ZoneInfo(pref.timezone)).strftime('%H:%M')
    start, end = pref.quiet_start, pref.quiet_end
    return start <= clock < end if start < end else clock >= start or clock < end


def digest_due(pref, created, at):
    local = created.astimezone(ZoneInfo(pref.timezone))
    hour, minute = map(int, pref.digest_time.split(':'))
    due = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if due <= local: due += timedelta(days=1)
    return at >= due.astimezone(timezone.utc)


def disposition(db, notice, at):
    sub = db.get(Subscription, notice.subscription_id)
    if not sub or not sub.enabled: return 'cancel'
    pref = db.get(NotificationPreference, sub.user_id)
    # Existing subscriptions retain their old behavior until the user saves preferences.
    if not pref: return 'instant'
    urgent = notice.reminder_id is not None and pref.urgent_override
    if quiet(pref, at) and not urgent: return 'wait'
    grouped = (pref.mode == 'daily' or notice.payload.get('delivery_class') == 'review_digest') and not urgent
    if grouped:
        return 'digest' if digest_due(pref, aware_time(notice.created_at), at) else 'wait'
    return 'instant'


def dispatch_local(at=None):
    at = at or datetime.now(timezone.utc)
    groups = {}
    with Session() as db:
        cancel_invalid_reminders(db, at)
        for notice in db.scalars(select(Outbox).where(Outbox.state == 'queued', Outbox.channel == 'in_app').order_by(Outbox.id)):
            action = disposition(db, notice, at)
            if action == 'cancel': notice.state = 'cancelled'
            elif action == 'instant': notice.state = 'accepted'
            elif action == 'digest':
                uid = db.get(Subscription, notice.subscription_id).user_id
                groups.setdefault(uid, []).append(notice)
        batches=[(uid,items[i:i+100]) for uid,items in groups.items() for i in range(0,len(items),100)]
        for uid, items in batches:
            # Claim each origin inside this transaction; digest membership is globally unique.
            claimed = []
            for item in items:
                if db.execute(update(Outbox).where(Outbox.id == item.id, Outbox.state == 'queued').values(state='accepted')).rowcount:
                    claimed.append(item)
            if not claimed: continue
            digest = Digest(user_id=uid, created_at=at.isoformat(),
                window_start=min(i.created_at for i in claimed), window_end=at.isoformat(),
                representative_id=claimed[0].id,
                sources=[{'id': s.id, 'enabled': s.enabled, 'status': s.status,
                          'coverage': s.coverage, 'last_success_at': s.last_success_at}
                         for s in db.scalars(select(Source))])
            db.add(digest); db.flush()
            for item in claimed: db.add(DigestItem(outbox_id=item.id, digest_id=digest.id))
        db.commit()
    return len(groups)


def email_origins(db, notice, at):
    """Only the representative of a batch is sent; cancelled members are excluded."""
    sub = db.get(Subscription, notice.subscription_id)
    pref = db.get(NotificationPreference, sub.user_id) if sub else None
    if quiet(pref, at) and not (pref and pref.urgent_override and notice.reminder_id): return []
    item = db.get(DigestItem, notice.id)
    if item:
        digest = db.get(Digest, item.digest_id)
        if digest.representative_id != notice.id: return []
        from .notifications import reminder_valid
        from .db import DeadlineReminder
        rows=db.scalars(select(Outbox).join(DigestItem).join(Subscription).where(
            DigestItem.digest_id == digest.id, Outbox.state == 'accepted', Subscription.enabled.is_(True)))
        return [r for r in rows if not r.reminder_id or reminder_valid(db, db.get(DeadlineReminder,r.reminder_id),at)]
    return [notice] if notice.state == 'accepted' or disposition(db, notice, at) == 'instant' else []
