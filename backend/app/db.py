from datetime import datetime, timezone
from sqlalchemy import create_engine, JSON, String, Integer, Text, ForeignKey, UniqueConstraint, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
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

class CrawlRun(Base):
    __tablename__ = 'crawl_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
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
    created_at: Mapped[str] = mapped_column(default=now)

class Event(Base):
    __tablename__ = 'change_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey('listing_versions.id'), unique=True)
    kind: Mapped[str]

class Outbox(Base):
    __tablename__ = 'notification_outbox'
    __table_args__ = (UniqueConstraint('subscription_id', 'event_id', 'channel'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey('subscriptions.id'))
    event_id: Mapped[int] = mapped_column(ForeignKey('change_events.id'))
    channel: Mapped[str] = mapped_column(default='in_app')
    state: Mapped[str] = mapped_column(default='queued')
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)
    read: Mapped[bool] = mapped_column(default=False)

class Followup(Base):
    __tablename__ = 'followups'
    __table_args__ = (UniqueConstraint('user_id', 'listing_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    listing_id: Mapped[int] = mapped_column(ForeignKey('listing_rounds.id'))
    status: Mapped[str] = mapped_column(default='未查看')
    note: Mapped[str] = mapped_column(Text, default='')
    favorite: Mapped[bool] = mapped_column(default=False)

def seed_sources(db):
    for sid, name, url in [
        ('nongjy', '农交云', 'https://www.nongjy.cn/web/propertyBid/list'),
        ('wzpt', '温州职业技术学院', 'https://www.wzpt.edu.cn/tzgg/list.htm'),
        ('wzcqpt', '温州联合产权交易中心（待适配）', 'https://www.wzcqpt.com/WZPT/'),
    ]:
        if not db.get(Source, sid):
            db.add(Source(id=sid, name=name, seed_url=url))
    db.commit()
