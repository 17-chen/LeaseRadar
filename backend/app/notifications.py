"""Business notices and deadline reminders share the transactional in-app outbox."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .db import Session, Subscription, Listing, Version, SourceRecord, Followup, Outbox, DeadlineReminder, Event, RawDocument
from .domain import match
from .config import MODE

TERMINAL_STATES = {'closed', 'withdrawn', 'sold', 'failed'}
STOPPED_FOLLOWUPS = {'放弃', '已成交'}
CHANGE_FIELDS = ('status', 'raw_amount', 'price_kind', 'period_basis', 'area_m2', 'address',
                 'registration_deadline', 'auction_deadline', 'operation', 'property_type', 'environment')

def aware_time(value):
    if not value: return None
    try:
        result = datetime.fromisoformat(value)
        return result.astimezone(timezone.utc) if result.tzinfo is not None else None
    except (ValueError, TypeError):
        return None

def stopped(db, user_id, listing_id):
    row = db.scalar(select(Followup).where(Followup.user_id == user_id, Followup.listing_id == listing_id))
    return bool(row and row.status in STOPPED_FOLLOWUPS)

def queue_change(db, listing, version, event, previous, url):
    """A former candidate becoming ineligible is information, not a new match."""
    fields = version.fields
    changes = [{'field': key, 'before': previous.fields.get(key), 'after': fields.get(key)}
               for key in CHANGE_FIELDS if previous and previous.fields.get(key) != fields.get(key)]
    for sub in db.scalars(select(Subscription).where(Subscription.enabled.is_(True))):
        result = match(fields, {**sub.filters, 'registration_open': True})
        informational = False
        if previous and result['verdict'] == 'fail':
            if stopped(db, sub.user_id, listing.id): continue
            prior_notice = db.scalar(select(Outbox.id).join(Event).join(Version).where(
                Outbox.subscription_id == sub.id, Version.listing_id == listing.id,
                Outbox.state.in_(['queued', 'accepted'])).limit(1))
            observation = aware_time(db.get(RawDocument, previous.raw_id).fetched_at)
            subscribed = aware_time(sub.created_at)
            previous_match = match(previous.fields, {**sub.filters, 'registration_open': True},
                                   max(observation, subscribed) if observation and subscribed else None)
            informational = bool(prior_notice or previous_match['verdict'] == 'pass' or
                                 (previous_match['verdict'] == 'unknown' and sub.unknown_policy != 'exclude'))
        if result['verdict'] == 'fail' and not informational: continue
        if result['verdict'] == 'unknown' and sub.unknown_policy == 'exclude': continue
        db.add(Outbox(subscription_id=sub.id, event_id=event.id, payload={
            'listing_id': listing.id, 'title': fields['title'], 'kind': event.kind, 'match': result,
            'notice_class': 'status_update' if informational else 'candidate', 'changes': changes,
            'delivery_class': 'instant' if informational or result['verdict'] == 'pass' else 'review_digest',
            'source_url': url, 'registration_deadline': fields.get('registration_deadline'),
            'mode': MODE}))

def lead_for(fields, hours, at):
    deadline = aware_time(fields.get('registration_deadline'))
    if not deadline or deadline <= at or fields.get('status') in TERMINAL_STATES: return None
    remaining = (deadline - at).total_seconds() / 3600
    candidates = [hour for hour in hours if remaining <= hour]
    return min(candidates) if candidates else None

def reminder_valid(db, reminder, at, *, pending=True):
    sub = db.get(Subscription, reminder.subscription_id)
    listing = db.get(Listing, reminder.listing_id)
    if not sub or not listing or not sub.enabled or stopped(db, sub.user_id, listing.id): return False
    version = db.get(Version, listing.current_version_id)
    deadline = aware_time(version.fields.get('registration_deadline'))
    if not deadline or deadline.isoformat() != reminder.deadline: return False
    if deadline <= at or version.fields.get('status') in TERMINAL_STATES: return False
    if reminder.lead_hours not in sub.reminder_hours: return False
    if pending and lead_for(version.fields, sub.reminder_hours, at) != reminder.lead_hours: return False
    if pending:
        record = db.scalar(select(SourceRecord).where(SourceRecord.listing_id == listing.id))
        checked = aware_time(record.last_checked_at) if record else None
        if not checked or not timedelta(0) <= at - checked <= timedelta(hours=24): return False
    result = match(version.fields, {**sub.filters, 'registration_open': True}, at)
    return result['verdict'] != 'fail' and (result['verdict'] != 'unknown' or sub.unknown_policy != 'exclude')

def cancel_invalid_reminders(db, at=None):
    at = at or datetime.now(timezone.utc)
    for notice in db.scalars(select(Outbox).where(Outbox.reminder_id.is_not(None), Outbox.state.in_(['queued', 'accepted']))):
        if not reminder_valid(db, db.get(DeadlineReminder, notice.reminder_id), at, pending=notice.state == 'queued'):
            notice.payload = {**notice.payload, 'accepted_before_cancellation': notice.state == 'accepted'}
            notice.state = 'cancelled'

def generate_deadline_reminders(at=None):
    at = at or datetime.now(timezone.utc)
    created = 0
    with Session() as db:
        cancel_invalid_reminders(db, at)
        subscriptions = list(db.scalars(select(Subscription).where(Subscription.enabled.is_(True))))
        for listing in db.scalars(select(Listing)):
            version = db.get(Version, listing.current_version_id)
            record = db.scalar(select(SourceRecord).where(SourceRecord.listing_id == listing.id))
            # Avoid fresh-sounding reminders based on stale or time-unknown observations.
            checked = aware_time(record.last_checked_at) if record else None
            if not version or not checked or not timedelta(0) <= at - checked <= timedelta(hours=24): continue
            fields = version.fields
            for sub in subscriptions:
                hour = lead_for(fields, sub.reminder_hours, at)
                if hour is None or stopped(db, sub.user_id, listing.id): continue
                result = match(fields, {**sub.filters, 'registration_open': True}, at)
                if result['verdict'] == 'fail' or (result['verdict'] == 'unknown' and sub.unknown_policy == 'exclude'): continue
                deadline = aware_time(fields['registration_deadline']).isoformat()
                existing = db.scalar(select(DeadlineReminder).where(DeadlineReminder.subscription_id == sub.id,
                       DeadlineReminder.listing_id == listing.id, DeadlineReminder.deadline == deadline,
                       DeadlineReminder.lead_hours == hour))
                payload = {
                    'listing_id': listing.id, 'title': fields['title'], 'kind': 'registration_reminder',
                    'notice_class': 'deadline_reminder', 'lead_hours': hour,
                    'registration_deadline': fields['registration_deadline'],
                    'last_checked_at': record.last_checked_at, 'match': result,
                    'delivery_class': 'instant' if result['verdict'] == 'pass' else 'review_digest',
                    'source_url': record.url, 'mode': MODE}
                if existing:
                    notice = db.scalar(select(Outbox).where(Outbox.reminder_id == existing.id, Outbox.channel == 'in_app'))
                    # Resume a cancelled unsent reminder by reusing its outbox identity.
                    # Already accepted or legacy unknown receipts are never automatically resent.
                    if notice and notice.state == 'cancelled' and notice.payload.get('accepted_before_cancellation') is False:
                        claimed = db.execute(update(Outbox).where(Outbox.id == notice.id, Outbox.state == 'cancelled')
                            .values(state='queued', payload=payload))
                        created += claimed.rowcount
                    continue
                try:
                    # Unique keys also protect concurrent worker cycles; reminder+outbox roll back together.
                    with db.begin_nested():
                        reminder = DeadlineReminder(subscription_id=sub.id, listing_id=listing.id,
                            version_id=version.id, deadline=deadline, lead_hours=hour, created_at=at.isoformat())
                        db.add(reminder); db.flush()
                        db.add(Outbox(subscription_id=sub.id, reminder_id=reminder.id, created_at=at.isoformat(), payload=payload))
                        db.flush()
                    created += 1
                except IntegrityError:
                    # Only a competing insertion of this same identity is safe to ignore.
                    if not db.scalar(select(DeadlineReminder.id).where(DeadlineReminder.subscription_id == sub.id,
                            DeadlineReminder.listing_id == listing.id, DeadlineReminder.deadline == deadline,
                            DeadlineReminder.lead_hours == hour)): raise
        db.commit()
    return created
