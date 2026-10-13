from datetime import datetime, timezone
from sqlalchemy import create_engine, event, JSON, String, Integer, Text, ForeignKey, UniqueConstraint, CheckConstraint, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def enforce_foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(default='member')

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[str] = mapped_column(String(50))

class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str]
    seed_url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(default='pending_validation')
    last_attempt_at: Mapped[str | None]
    last_success_at: Mapped[str | None]
    error: Mapped[str | None] = mapped_column(Text)
    lease_until: Mapped[str | None]
    coverage: Mapped[str | None]
    next_run_at: Mapped[str | None]
    backfill_page: Mapped[int] = mapped_column(default=1)
    backfill_at: Mapped[str | None]
    total_pages: Mapped[int | None]
    detail_next_run_at: Mapped[str | None]
    detail_last_success_at: Mapped[str | None]
    detail_checked: Mapped[int] = mapped_column(default=0)
    lease_token: Mapped[str | None]
    daily_page_budget: Mapped[int] = mapped_column(default=48)
    backfill_batch_pages: Mapped[int] = mapped_column(default=3)

class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    created_at: Mapped[str] = mapped_column(default=now)
    state: Mapped[str] = mapped_column(default='queued')
    lease_until: Mapped[str | None]
    kind: Mapped[str] = mapped_column(default="front")
    attempts: Mapped[int] = mapped_column(default=0)
    retry_at: Mapped[str | None]
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    lease_token: Mapped[str | None]

class CrawlRun(Base):
    __tablename__ = 'crawl_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    kind: Mapped[str] = mapped_column(default='front')
    started_at: Mapped[str] = mapped_column(default=now)
    ended_at: Mapped[str | None]
    state: Mapped[str] = mapped_column(default='running')
    pages: Mapped[int] = mapped_column(default=0)
    discovered: Mapped[int] = mapped_column(default=0)
    stored: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)

class RawDocument(Base):
    __tablename__ = 'raw_documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[str] = mapped_column(default=now)
    sha256: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    snapshot_path: Mapped[str] = mapped_column(Text)

class Asset(Base):
    __tablename__ = 'assets'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str | None] = mapped_column(Text)

class Listing(Base):
    __tablename__ = 'listing_rounds'
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    created_at: Mapped[str] = mapped_column(default=now)
    current_version_id: Mapped[int | None]

class SourceRecord(Base):
    __tablename__ = 'source_records'
    __table_args__ = (UniqueConstraint('source_id', 'record_id', 'lot_code'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    record_id: Mapped[str]
    lot_code: Mapped[str] = mapped_column(default='1')
    listing_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    url: Mapped[str] = mapped_column(Text)
    last_checked_at: Mapped[str] = mapped_column(default=now)

class Version(Base):
    __tablename__ = 'listing_versions'
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    raw_id: Mapped[int] = mapped_column(ForeignKey('raw_documents.id'))
    created_at: Mapped[str] = mapped_column(default=now)
    business_hash: Mapped[str] = mapped_column(String(64))
    fields: Mapped[dict] = mapped_column(JSON)
    first_year_monthly: Mapped[object | None] = mapped_column(Numeric(18, 4))
    area_m2: Mapped[object | None] = mapped_column(Numeric(18, 4))

class Evidence(Base):
    __tablename__ = 'field_evidence'
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey('listing_versions.id'))
    field: Mapped[str]
    quote: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(default='html_rule')

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str]
    filters: Mapped[dict] = mapped_column(JSON)
    unknown_policy: Mapped[str] = mapped_column(default='review_digest')
    enabled: Mapped[bool] = mapped_column(default=True)
    reminder_hours: Mapped[list] = mapped_column(JSON, default=lambda: [72, 24])
    created_at: Mapped[str] = mapped_column(default=now)

class Event(Base):
    __tablename__ = 'change_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey('listing_versions.id'), unique=True)
    kind: Mapped[str]

class DeadlineReminder(Base):
    __tablename__ = 'deadline_reminders'
    __table_args__ = (UniqueConstraint('subscription_id', 'listing_id', 'deadline', 'lead_hours'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey('subscriptions.id'))
    listing_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    version_id: Mapped[int] = mapped_column(ForeignKey('listing_versions.id'))
    deadline: Mapped[str] = mapped_column(String(50))
    lead_hours: Mapped[int]
    created_at: Mapped[str] = mapped_column(default=now)

class Outbox(Base):
    __tablename__ = 'notification_outbox'
    __table_args__ = (UniqueConstraint('subscription_id', 'event_id', 'channel'),
                     UniqueConstraint('reminder_id', 'channel'),
                     CheckConstraint('(event_id IS NOT NULL AND reminder_id IS NULL) OR (event_id IS NULL AND reminder_id IS NOT NULL)', name='outbox_one_origin'))
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey('subscriptions.id'))
    event_id: Mapped[int | None] = mapped_column(ForeignKey('change_events.id'))
    reminder_id: Mapped[int | None] = mapped_column(ForeignKey('deadline_reminders.id'))
    channel: Mapped[str] = mapped_column(default='in_app')
    state: Mapped[str] = mapped_column(default='queued')
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)
    read: Mapped[bool] = mapped_column(default=False)

class EmailDelivery(Base):
    __tablename__ = 'email_deliveries'
    id: Mapped[int] = mapped_column(primary_key=True)
    outbox_id: Mapped[int] = mapped_column(ForeignKey('notification_outbox.id'), unique=True)
    manual_retry: Mapped[bool] = mapped_column(default=False)
    message_id: Mapped[str | None]
    sender_address: Mapped[str | None]
    recipient: Mapped[str]
    state: Mapped[str] = mapped_column(default='queued')
    attempts: Mapped[int] = mapped_column(default=0)
    retry_at: Mapped[str | None]
    lease_until: Mapped[str | None]
    token: Mapped[str | None]
    error: Mapped[str | None]
    accepted_at: Mapped[str | None]

class Followup(Base):
    __tablename__ = 'followups'
    __table_args__ = (UniqueConstraint('user_id', 'listing_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    listing_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    status: Mapped[str] = mapped_column(default='未查看')
    note: Mapped[str] = mapped_column(Text, default='')
    favorite: Mapped[bool] = mapped_column(default=False)

class NotificationPreference(Base):
    __tablename__ = 'notification_preferences'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    mode: Mapped[str] = mapped_column(default='instant')
    timezone: Mapped[str] = mapped_column(default='Asia/Shanghai')
    digest_time: Mapped[str] = mapped_column(default='09:00')
    quiet_start: Mapped[str | None]
    quiet_end: Mapped[str | None]
    urgent_override: Mapped[bool] = mapped_column(default=False)

class Digest(Base):
    __tablename__ = 'notification_digests'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[str] = mapped_column(default=now)
    window_start: Mapped[str]
    window_end: Mapped[str]
    representative_id: Mapped[int] = mapped_column(ForeignKey('notification_outbox.id'), unique=True)
    sources: Mapped[list] = mapped_column(JSON)

class DigestItem(Base):
    __tablename__ = 'notification_digest_items'
    outbox_id: Mapped[int] = mapped_column(ForeignKey('notification_outbox.id'), primary_key=True)
    digest_id: Mapped[int] = mapped_column(ForeignKey('notification_digests.id'))

class Correction(Base):
    __tablename__ = 'corrections'
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    field: Mapped[str]
    value: Mapped[object | None] = mapped_column(JSON)
    original: Mapped[object | None] = mapped_column(JSON)
    quote: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    base_version_id: Mapped[int] = mapped_column(ForeignKey('listing_versions.id'))
    version_id: Mapped[int | None] = mapped_column(ForeignKey('listing_versions.id'))
    state: Mapped[str] = mapped_column(default='active')
    created_at: Mapped[str] = mapped_column(default=now)
    resolved_at: Mapped[str | None]

class ListingRelation(Base):
    __tablename__ = 'listing_relations'
    __table_args__ = (UniqueConstraint('left_id', 'right_id', 'kind'), CheckConstraint('left_id < right_id', name='relation_order'))
    id: Mapped[int] = mapped_column(primary_key=True)
    left_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    right_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    kind: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    reason: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(default='active')
    created_at: Mapped[str] = mapped_column(default=now)
    resolved_at: Mapped[str | None]

class AuditAction(Base):
    __tablename__ = 'audit_actions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str]
    object_id: Mapped[int]
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)

class SourceIncident(Base):
    __tablename__ = 'source_incidents'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    kind: Mapped[str]
    state: Mapped[str] = mapped_column(default='open')
    message: Mapped[str] = mapped_column(Text)
    opened_at: Mapped[str] = mapped_column(default=now)
    resolved_at: Mapped[str | None]

class SourcePageObservation(Base):
    __tablename__ = 'source_page_observations'
    __table_args__ = (UniqueConstraint('source_id','page'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    page: Mapped[int]
    checked_at: Mapped[str] = mapped_column(default=now)

def seed_sources(db):
    for sid, name, url in [
        ('nongjy', '农交云', 'https://www.nongjy.cn/web/propertyBid/list'),
        ('wzpt', '温州职业技术学院', 'https://www.wzpt.edu.cn/tzgg/list.htm'),
        ('wzcqpt', '温州联合产权交易中心（待适配）', 'https://www.wzcqpt.com/WZPT/'),
    ]:
        if not db.get(Source, sid):
            db.add(Source(id=sid, name=name, seed_url=url))
    db.commit()

class DocumentReview(Base):
    __tablename__ = 'document_reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    listing_id: Mapped[int | None] = mapped_column(ForeignKey('listing_rounds.id'))
    filename: Mapped[str]
    sha256: Mapped[str] = mapped_column(String(64))
    format: Mapped[str]
    state: Mapped[str] = mapped_column(default='queued')
    pages: Mapped[list] = mapped_column(JSON,default=list)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)

class IncidentEmail(Base):
    __tablename__='incident_emails'
    __table_args__=(UniqueConstraint('incident_id','phase'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    incident_id: Mapped[int]=mapped_column(ForeignKey('source_incidents.id'))
    manual_retry: Mapped[bool]=mapped_column(default=False)
    message_id: Mapped[str | None]
    sender_address: Mapped[str | None]
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    phase: Mapped[str]
    recipient: Mapped[str]
    state: Mapped[str]=mapped_column(default='queued')
    attempts: Mapped[int]=mapped_column(default=0)
    retry_at: Mapped[str | None]
    lease_until: Mapped[str | None]
    token: Mapped[str | None]
    error: Mapped[str | None]
    accepted_at: Mapped[str | None]
    created_at: Mapped[str]=mapped_column(default=now)
