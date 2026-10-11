"""Measured coverage and durable incidents, never a claim of a consistent snapshot."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from .db import Session, Source, SourceIncident, SourcePageObservation, CrawlRun, SourceRecord
from .domain import aware_time


def metrics(db, source, at=None):
    at=at or datetime.now(timezone.utc)
    midnight=at.astimezone(ZoneInfo('Asia/Shanghai')).replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).isoformat()
    pages=db.scalar(select(func.count()).select_from(SourcePageObservation).where(SourcePageObservation.source_id==source.id,SourcePageObservation.checked_at>=midnight))
    spent=db.scalar(select(func.coalesce(func.sum(CrawlRun.pages),0)).where(CrawlRun.source_id==source.id,CrawlRun.kind=='backfill',CrawlRun.started_at>=midnight))
    oldest=db.scalar(select(func.min(SourceRecord.last_checked_at)).where(SourceRecord.source_id==source.id))
    return {'pages_today':pages,'known_total_pages':source.total_pages,'backfill_pages_today':spent,
            'daily_page_budget':source.daily_page_budget,'remaining_budget':max(0,source.daily_page_budget-spent),
            'backfill_batch_pages':source.backfill_batch_pages,'oldest_detail_check':oldest,
            'warning':'动态列表可能移动；页数覆盖不等于完整一致快照'}


def observe_page(db, source_id, page):
    row=db.scalar(select(SourcePageObservation).where(SourcePageObservation.source_id==source_id,SourcePageObservation.page==page))
    if not row:db.add(SourcePageObservation(source_id=source_id,page=page))
    else:row.checked_at=datetime.now(timezone.utc).isoformat()


def sync_incidents(at=None):
    at=at or datetime.now(timezone.utc)
    with Session() as db:
        for source in db.scalars(select(Source)):
            checked=aware_time(source.last_success_at)
            current={}
            if source.error:current['source_error']=source.error
            if source.enabled and (not checked or at-checked>timedelta(hours=2)):
                current['stale']='已启用来源超过2小时没有成功观测，候选可能陈旧'
            for row in db.scalars(select(SourceIncident).where(SourceIncident.source_id==source.id,SourceIncident.state=='open')):
                if row.kind not in current:row.state='resolved';row.resolved_at=at.isoformat()
                else:row.message=current.pop(row.kind)
            for kind,message in current.items():db.add(SourceIncident(source_id=source.id,kind=kind,message=message,opened_at=at.isoformat()))
        db.commit()
