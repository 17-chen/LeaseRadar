import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select, update
from .db import Session, Source, Job, CrawlRun, RawDocument, Asset, Listing, SourceRecord, Version, Evidence, Subscription, Event, Outbox, now
from .config import DATA, MODE
from .domain import normalize_price, match, decimal
from .collectors import fetch, PARSERS, DISCOVERERS, SourceError

def ingest(db, source_id, url, html, event_kind=None, attachment_cache=None):
    fields, evidence, text = PARSERS[source_id](html, url)
    if attachment_cache is not None and source_id == 'nongjy':
        from .attachments import enrich_docx
        enrich_docx(fields, evidence, attachment_cache)
        fields['parser_version'] = 'nongjy-html-docx-v3'
    fields.update(normalize_price(fields))
    content_hash = hashlib.sha256(html.encode()).hexdigest()
    snapshot_dir = DATA / 'snapshots'
    snapshot_dir.mkdir(exist_ok=True)
    path = snapshot_dir / (content_hash + '.html')
    path.write_text(html)
    raw = RawDocument(url=url, sha256=content_hash, text=text, snapshot_path=str(path))
    db.add(raw); db.flush()
    record_id = url.rstrip('/').split('/')[-1]
    record = db.scalar(select(SourceRecord).where(SourceRecord.source_id == source_id, SourceRecord.record_id == record_id, SourceRecord.lot_code == '1'))
    is_new = record is None
    if is_new:
        # Conservative: cross-source association is a later human-reviewed operation.
        asset = Asset(address=fields.get('address')); db.add(asset); db.flush()
        listing = Listing(asset_id=asset.id); db.add(listing); db.flush()
        record = SourceRecord(source_id=source_id, record_id=record_id, listing_id=listing.id, url=url)
        db.add(record)
    else:
        listing = db.get(Listing, record.listing_id)
    record.last_checked_at = now()
    business_hash = hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    previous = db.get(Version, listing.current_version_id) if listing.current_version_id else None
    if previous and previous.business_hash == business_hash:
        return listing.id, False
    # A previous state can recur. Versions describe observations rather than globally unique hashes.
    version = Version(listing_id=listing.id, raw_id=raw.id, business_hash=business_hash,
                      fields=fields, first_year_monthly=decimal(fields.get('first_year_monthly')), area_m2=decimal(fields.get('area_m2')))
    db.add(version); db.flush()
    listing.current_version_id = version.id
    for field, quote in evidence.items(): db.add(Evidence(version_id=version.id, field=field, quote=quote))
    reprocessing = False
    if previous:
        old_files = {a['url']: a.get('sha256') for a in previous.fields.get('attachments', [])}
        new_files = {a['url']: a.get('sha256') for a in fields.get('attachments', [])}
        same_html = db.get(RawDocument, previous.raw_id).sha256 == content_hash
        incomplete_files = any(digest is None for digest in new_files.values())
        reprocessing = previous.fields.get('parser_version') != fields.get('parser_version') or (same_html and (old_files == new_files or incomplete_files))
    kind = event_kind or ('new' if is_new else 'reprocessing' if reprocessing else 'changed')
    if previous and not reprocessing and not event_kind:
        old = previous.fields
        if old.get('status') != fields.get('status'):
            kind = 'status_changed'
        elif old.get('registration_deadline') and fields.get('registration_deadline') and fields['registration_deadline'] > old['registration_deadline']:
            kind = 'deadline_extended'
        elif old.get('period_basis') == fields.get('period_basis') and old.get('price_kind') == fields.get('price_kind') and decimal(old.get('raw_amount')) is not None and decimal(fields.get('raw_amount')) is not None and decimal(fields['raw_amount']) < decimal(old['raw_amount']):
            kind = 'price_drop'
    event = Event(version_id=version.id, kind=kind); db.add(event); db.flush()
    if kind == 'reprocessing': return listing.id, True
    for sub in db.scalars(select(Subscription).where(Subscription.enabled.is_(True))):
        result = match(fields, {**sub.filters, 'registration_open': True})
        if result['verdict'] == 'fail' or (result['verdict'] == 'unknown' and sub.unknown_policy == 'exclude'):
            continue
        db.add(Outbox(subscription_id=sub.id, event_id=event.id, payload={
            'listing_id': listing.id, 'title': fields['title'], 'kind': kind,
            'match': result, 'delivery_class': 'review_digest' if result['verdict'] == 'unknown' else 'instant',
            'source_url': url, 'mode': MODE}))
    return listing.id, True

def crawl(source_id, pages=1, delay=2.5, *, backfill=False):
    if not 1 <= pages <= 10: raise ValueError("单次任务限1–10页")
    if source_id not in PARSERS:
        raise SourceError('该来源尚未实现适配器')
    lease_time = (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat()
    with Session() as db:
        source = db.get(Source, source_id)
        if not source: raise SourceError('来源不存在')
        # Atomic compare-and-set works on PostgreSQL and local SQLite.
        claim = db.execute(update(Source).where(Source.id == source_id, (Source.lease_until.is_(None)) | (Source.lease_until < now())).values(lease_until=lease_time, last_attempt_at=now()))
        if not claim.rowcount: raise SourceError('来源任务已运行', retryable=True)
        run = CrawlRun(source_id=source_id); db.add(run); db.commit()
        run_id, seed = run.id, source.seed_url
        start_page = source.backfill_page if backfill else 1
    try:
        import time
        seen = set(); total = 1; attachment_cache = {}
        for page in range(start_page, start_page + pages):
            url = seed + f'?pageNum={page}&pageSize=12' if source_id == 'nongjy' else seed if page == 1 else seed.replace('list.htm', f'list{page}.htm')
            html = fetch(url)
            refs, total = DISCOVERERS[source_id](html, page)
            if not refs and source_id != 'wzpt':
                raise SourceError('当前扫描页没有招租链接，需人工复核栏目；未视为覆盖成功')
            if refs and page > 1 and set(refs).issubset(seen):
                raise SourceError('分页重复，拒绝伪报完整覆盖')
            for ref in refs:
                if ref in seen: continue
                seen.add(ref); time.sleep(delay)
                body = fetch(ref)
                with Session() as db:
                    ingest(db, source_id, ref, body, attachment_cache=attachment_cache)
                    run = db.get(CrawlRun, run_id)
                    run.discovered += 1; run.stored += 1
                    db.commit()
            with Session() as db:
                run = db.get(CrawlRun, run_id); run.pages += 1
                source = db.get(Source, source_id)
                source.total_pages = total
                if backfill: source.backfill_page = page + 1 if page < total else 1
                # Renew after each completed page; incomplete pages retain their cursor.
                source.lease_until = (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat()
                db.commit()
            if page >= total: break
            time.sleep(delay)
        with Session() as db:
            source = db.get(Source, source_id); run = db.get(CrawlRun, run_id)
            source.status = 'partial' if run.pages < total else 'healthy'
            source.coverage = f'本次第{start_page}–{start_page + run.pages - 1}页 / {total}页；回扫下一页{source.backfill_page}（不保证列表快照完整）'
            source.last_success_at = now(); source.error = None; source.lease_until = None
            run.state = source.status; run.ended_at = now(); db.commit()
        return {'run_id': run_id, 'pages': run.pages, 'start_page': start_page, 'total_pages': total, 'records': len(seen)}
    except Exception as exc:
        with Session() as db:
            source = db.get(Source, source_id); run = db.get(CrawlRun, run_id)
            source.status = 'blocked' if getattr(exc, 'blocked', False) or 'HTTP 403' in str(exc) else 'degraded'
            source.error = str(exc)[:500]; source.lease_until = None
            if source.status == 'blocked': source.enabled = False
            run.state = 'failed'; run.error = source.error; run.ended_at = now(); db.commit()
        raise

def deliver_local():
    with Session() as db:
        # In-app acceptance is an atomic database state transition; no external send.
        db.execute(update(Outbox).where(Outbox.state == 'queued', Outbox.channel == 'in_app').values(state='accepted'))
        db.commit()

def enqueue(db, source_id, kind="front"):
    if kind not in ("front", "backfill"): raise ValueError("未知采集任务类型")
    pending = db.scalar(select(Job).where(Job.source_id == source_id, Job.state.in_(['queued', 'running', 'retry_wait'])))
    if pending: return pending.id
    row = Job(source_id=source_id, kind=kind); db.add(row); db.flush()
    return row.id

def job_due():
    return (Job.state == 'queued') | ((Job.state == 'retry_wait') & (Job.retry_at <= now())) | ((Job.state == 'running') & (Job.lease_until < now()))

def poll_jobs():
    import httpx
    with Session() as db:
        for source in db.scalars(select(Source).where(Source.enabled.is_(True))):
            if db.scalar(select(Job.id).where(Job.source_id == source.id, Job.state.in_(['queued', 'running', 'retry_wait']))):
                continue
            # A completed front check is followed by one bounded backfill page.
            if not source.next_run_at or source.next_run_at <= now():
                enqueue(db, source.id)
                source.next_run_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
            elif not source.backfill_at or source.backfill_at <= now():
                enqueue(db, source.id, 'backfill')
                source.backfill_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        db.commit()
        jobs = list(db.scalars(select(Job.id).where(job_due())))
    for jid in jobs:
        with Session() as db:
            claimed = db.execute(update(Job).where(Job.id == jid, job_due()).values(state='running', attempts=Job.attempts + 1, retry_at=None, lease_until=(datetime.now(timezone.utc)+timedelta(minutes=65)).isoformat()))
            db.commit()
            if not claimed.rowcount: continue
            job = db.get(Job, jid); sid, kind = job.source_id, job.kind
        try:
            result = crawl(sid, backfill=True) if kind == 'backfill' else crawl(sid)
            with Session() as db:
                job = db.get(Job, jid); job.state = 'complete'; job.result = result; job.error = None; job.lease_until = None; db.commit()
        except Exception as exc:
            with Session() as db:
                job = db.get(Job, jid)
                retryable = getattr(exc, 'retryable', False) or isinstance(exc, httpx.TransportError)
                blocked = getattr(exc, 'blocked', False) or 'HTTP 403' in str(exc)
                if retryable and not blocked and job.attempts < 3:
                    delay = max(60 * 2 ** (job.attempts - 1), getattr(exc, 'retry_after', None) or 0)
                    job.retry_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
                    job.state = 'retry_wait'
                else:
                    job.state = 'failed'
                    # Exhausted or invalid sources require explicit admin resumption.
                    db.get(Source, sid).enabled = False
                job.error = str(exc)[:500]; job.lease_until = None; db.commit()
    deliver_local()

def listing_data(db, listing, user_id=None):
    version = db.get(Version, listing.current_version_id)
    record = db.scalar(select(SourceRecord).where(SourceRecord.listing_id == listing.id))
    if not version: return None
    from .db import Followup
    followup = db.scalar(select(Followup).where(Followup.listing_id == listing.id, Followup.user_id == user_id)) if user_id else None
    return {'id': listing.id, **version.fields, 'version_id': version.id, 'source_id': record.source_id,
            'last_checked_at': record.last_checked_at, 'created_at': listing.created_at,
            'followup': {'status': followup.status, 'note': followup.note, 'favorite': followup.favorite} if followup else None}
