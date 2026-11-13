"""Durable, opt-in source attachment GETs. Extraction stays in the isolated worker."""
import base64
import hashlib
import os
import secrets
import time
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit
import httpx
from sqlalchemy import select,update,func
from sqlalchemy.exc import IntegrityError
from .db import Session,DocumentDownload,DocumentReview,Version,SourceRecord,Source,Listing,RawDocument,now
from .source_documents import configuration
from .document_jobs import upload
from .collectors import stream_public,response_error,SourceError

MAX_BYTES=5_000_000
SOURCE_HOSTS={'nongjy':'www.nongjy.cn','wzpt':'www.wzpt.edu.cn'}


def version_belongs_to_source(db,version,source_id):
    """A merged listing may have records from several sources; use the raw origin."""
    raw=db.get(RawDocument,version.raw_id) if version else None
    if raw is None:return False
    try:return urlsplit(raw.url).hostname==SOURCE_HOSTS.get(source_id)
    except ValueError:return False


def owner(db):
    if os.getenv('SOURCE_DOCUMENT_DOWNLOADS_ENABLED','false').lower()!='true':return None
    user=configuration(db)
    if user is None:raise ValueError('附件下载须先配置来源附件审核管理员')
    return user


def format_for(url):
    if not isinstance(url,str) or len(url)>2000:return None
    try:
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname not in ('www.nongjy.cn','www.wzpt.edu.cn','www.wzcqpt.com') or p.username or p.password or p.port not in (None,443) or p.fragment:return None
    except ValueError:return None
    return 'pdf' if p.path.lower().endswith('.pdf') else 'docx' if p.path.lower().endswith('.docx') else None


def download_candidates(db,version,record):
    """Bounded metadata inspection, shared by ingestion and historical backfill."""
    files=version.fields.get('attachments',[])
    if not isinstance(files,list):return []
    result=[];seen=set()
    for item in files[:20]:
        if not isinstance(item,dict) or item.get('sha256'):continue
        url=item.get('url');kind=format_for(url)
        if not kind or url in seen:continue
        seen.add(url)
        if db.scalar(select(DocumentDownload.id).where(DocumentDownload.source_id==record.source_id,DocumentDownload.url==url,DocumentDownload.state=='blocked')):continue
        if db.scalar(select(DocumentDownload.id).where(DocumentDownload.version_id==version.id,DocumentDownload.url==url)):continue
        result.append((url,kind))
    return result


def enqueue_downloads(db,version,source_id):
    try:user_id=owner(db)
    except ValueError:return 0
    if user_id is None:return 0
    if not version_belongs_to_source(db,version,source_id):return 0
    query=select(SourceRecord).where(SourceRecord.listing_id==version.listing_id)
    query=query.where(SourceRecord.source_id==source_id)
    record=db.scalar(query.order_by(SourceRecord.id))
    if not record:return 0
    pending=db.scalar(select(func.count()).select_from(DocumentDownload).where(DocumentDownload.user_id==user_id,DocumentDownload.state.in_(['queued','retry_wait','downloading'])))
    count=0
    for url,kind in download_candidates(db,version,record):
        if count>=5 or pending>=20:break
        try:
            with db.begin_nested():
                db.add(DocumentDownload(version_id=version.id,source_id=record.source_id,user_id=user_id,url=url,format=kind));db.flush()
        except IntegrityError:continue
        count+=1;pending+=1
    return count


def backfill_downloads(db,source_id,after_listing=0,limit=25,apply=False):
    """Plan/enqueue one bounded batch. Caller commits before using the cursor.

    Inspect current versions only. A partially queued listing is deliberately
    revisited, so queue capacity never causes the cursor to skip its attachments.
    Neither mode fetches URLs, republishes versions, or retries terminal jobs.
    """
    if source_id not in ('nongjy','wzpt'):raise ValueError('未知来源')
    if not isinstance(after_listing,int) or after_listing<0:raise ValueError('游标须为非负挂牌ID')
    if not isinstance(limit,int) or not 1<=limit<=100:raise ValueError('单批挂牌数须为1–100')
    if apply:
        connection=db.connection()
        # sqlite3 legacy transaction control does not BEGIN for SELECT/SAVEPOINT.
        # Unlike ingestion, this entry point has no earlier INSERT. Keep nested
        # uniqueness savepoints inside a real transaction owned by the caller.
        if connection.dialect.name=='sqlite' and not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql('BEGIN')
    user_id=owner(db)
    if user_id is None:raise ValueError('附件补扫须先启用来源附件审核及下载，并配置管理员')
    pending=db.scalar(select(func.count()).select_from(DocumentDownload).where(DocumentDownload.user_id==user_id,DocumentDownload.state.in_(['queued','retry_wait','downloading'])))
    rows=db.scalars(select(Listing).where(Listing.id.in_(select(SourceRecord.listing_id).where(SourceRecord.source_id==source_id)),Listing.id>after_listing).order_by(Listing.id).limit(limit+1)).all()
    result={'mode':'apply' if apply else 'preview','source':source_id,'scanned':0,'planned':0,'queued':0,'after_listing':after_listing,'next_after_listing':after_listing,'has_more':len(rows)>limit,'stop':'batch_limit' if len(rows)>limit else 'complete'}
    for listing in rows[:limit]:
        result['scanned']+=1
        record=db.scalar(select(SourceRecord).where(SourceRecord.listing_id==listing.id,SourceRecord.source_id==source_id).order_by(SourceRecord.id))
        version=db.get(Version,listing.current_version_id) if listing.current_version_id else None
        candidates=download_candidates(db,version,record) if version_belongs_to_source(db,version,source_id) else []
        available=min(5,max(0,20-pending))
        planned=min(available,len(candidates))
        result['planned']+=planned
        queued=enqueue_downloads(db,version,source_id=source_id) if apply and planned else 0
        result['queued']+=queued
        pending+=queued if apply else planned
        if len(candidates)>(queued if apply else planned):
            result['has_more']=True
            result['stop']='queue_capacity' if pending>=20 else 'listing_limit'
            break
        result['next_after_listing']=listing.id
    return result


def download(url,kind):
    if format_for(url)!=kind:raise SourceError('附件URL或格式不在核准范围')
    start=time.monotonic()
    with stream_public(url) as response:
        if response.status_code!=200:raise response_error(response)
        length=response.headers.get('content-length')
        if length:
            try:size=int(length)
            except ValueError:raise SourceError('附件长度声明无效')
            if not 0<size<=MAX_BYTES:raise SourceError('附件长度超过5MB边界')
        data=bytearray()
        for chunk in response.iter_bytes():
            if time.monotonic()-start>60:raise SourceError('附件下载超过总时限',retryable=True)
            data.extend(chunk)
            if len(data)>MAX_BYTES:raise SourceError('附件超过5MB边界')
    data=bytes(data)
    if not data or not (data.startswith(b'%PDF-') if kind=='pdf' else data.startswith(b'PK')):raise SourceError('附件格式签名不符，保留待复核')
    return data


def eligible(db,row,user_id):
    version=db.get(Version,row.version_id)
    listing=db.get(Listing,version.listing_id) if version else None
    return (row.user_id==user_id and listing is not None and listing.current_version_id==row.version_id
            and version_belongs_to_source(db,version,row.source_id))


def process_download():
    """One GET per poll, shared source lease and token-CAS finalization."""
    with Session() as db:
        try:user_id=owner(db)
        except ValueError:return
        if user_id is None:return
        at=now()
        # A GET is safe to reattempt, but expired workers cannot publish results.
        for row in db.scalars(select(DocumentDownload).where(DocumentDownload.state=='downloading',DocumentDownload.lease_until<at).limit(20)):
            row.state='failed' if row.attempts>=3 else 'retry_wait';row.retry_at=at
            row.error='下载租约过期，保留尝试记录';row.token=None;row.lease_until=None
        db.commit()
        due=select(DocumentDownload).where(DocumentDownload.state.in_(['queued','retry_wait']), (DocumentDownload.retry_at.is_(None)) | (DocumentDownload.retry_at<=at)).order_by(DocumentDownload.id).limit(20)
        identity=None
        for row in db.scalars(due):
            if not eligible(db,row,user_id):row.state='cancelled';row.error='管理员归属或当前版本已变化';db.commit();continue
            pending=db.scalar(select(func.count()).select_from(DocumentReview).where(DocumentReview.user_id==user_id,DocumentReview.state=='queued'))
            if pending>=20:return
            token=secrets.token_hex(16);until=(datetime.now(timezone.utc)+timedelta(minutes=3)).isoformat()
            source_claim=db.execute(update(Source).where(Source.id==row.source_id,(Source.lease_until.is_(None)) | (Source.lease_until<at)).values(lease_token=token,lease_until=until))
            if not source_claim.rowcount:db.rollback();continue
            claimed=db.execute(update(DocumentDownload).where(DocumentDownload.id==row.id,DocumentDownload.state.in_(['queued','retry_wait']),DocumentDownload.attempts<3).values(state='downloading',token=token,lease_until=until,attempts=DocumentDownload.attempts+1,retry_at=None))
            if not claimed.rowcount:db.rollback();continue
            identity=row.id;url=row.url;kind=row.format;source_id=row.source_id;db.commit();break
        if identity is None:return
    data=None;error=None
    try:data=download(url,kind)
    except Exception as exc:error=exc
    with Session() as db:
        at=now()
        claimed=db.execute(update(DocumentDownload).where(DocumentDownload.id==identity,DocumentDownload.state=='downloading',DocumentDownload.token==token,DocumentDownload.lease_until>at).values(token=None,lease_until=None))
        if not claimed.rowcount:return
        source_claim=db.execute(update(Source).where(Source.id==source_id,Source.lease_token==token,Source.lease_until>at).values(lease_token=None,lease_until=(datetime.now(timezone.utc)+timedelta(seconds=3)).isoformat()))
        if not source_claim.rowcount:db.rollback();return
        row=db.get(DocumentDownload,identity)
        try:current_owner=owner(db)
        except ValueError:current_owner=None
        if current_owner is None or not eligible(db,row,current_owner):row.state='cancelled';row.error='下载后配置/当前版本已变化，未发布审核';db.commit();return
        if error is not None:
            row.error=str(error)[:500]
            if getattr(error,'blocked',False):row.state='blocked'
            elif (getattr(error,'retryable',False) or isinstance(error,httpx.TransportError)) and row.attempts<3:
                delay=max(60*2**(row.attempts-1),getattr(error,'retry_after',None) or 0)
                row.state='retry_wait';row.retry_at=(datetime.now(timezone.utc)+timedelta(seconds=delay)).isoformat()
                db.get(Source,source_id).lease_until=row.retry_at
            else:row.state='failed'
            db.commit();return
        version=db.get(Version,row.version_id);digest=hashlib.sha256(data).hexdigest()
        review=db.scalar(select(DocumentReview).where(DocumentReview.listing_id==version.listing_id,DocumentReview.origin_url==url,DocumentReview.sha256==digest))
        if review is None:
            try:
                with db.begin_nested():
                    review=upload(db,row.user_id,version.listing_id,f'来源下载-{digest[:12]}.{kind}',base64.b64encode(data).decode())
                    review.origin_version_id=version.id;review.origin_url=url;db.flush()
            except IntegrityError:
                review=db.scalar(select(DocumentReview).where(DocumentReview.listing_id==version.listing_id,DocumentReview.origin_url==url,DocumentReview.sha256==digest))
                if review is None:raise
        row.state='downloaded';row.sha256=digest;row.review_id=review.id;row.error=None;db.commit()
