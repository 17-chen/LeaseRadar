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
from .db import Session,DocumentDownload,DocumentReview,Version,SourceRecord,Source,Listing,now
from .source_documents import configuration
from .document_jobs import upload
from .collectors import stream_public,response_error,SourceError

MAX_BYTES=5_000_000


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


def enqueue_downloads(db,version):
    try:user_id=owner(db)
    except ValueError:return 0
    if user_id is None:return 0
    record=db.scalar(select(SourceRecord).where(SourceRecord.listing_id==version.listing_id))
    if not record:return 0
    files=version.fields.get('attachments',[])
    if not isinstance(files,list):return 0
    pending=db.scalar(select(func.count()).select_from(DocumentDownload).where(DocumentDownload.user_id==user_id,DocumentDownload.state.in_(['queued','retry_wait','downloading'])))
    count=0
    for item in files[:20]:
        if count>=5 or pending>=20:break
        if not isinstance(item,dict) or item.get('sha256'):continue
        url=item.get('url');kind=format_for(url)
        if not kind:continue
        if db.scalar(select(DocumentDownload.id).where(DocumentDownload.source_id==record.source_id,DocumentDownload.url==url,DocumentDownload.state=='blocked')):continue
        if db.scalar(select(DocumentDownload.id).where(DocumentDownload.version_id==version.id,DocumentDownload.url==url)):continue
        try:
            with db.begin_nested():
                db.add(DocumentDownload(version_id=version.id,source_id=record.source_id,user_id=user_id,url=url,format=kind));db.flush()
        except IntegrityError:continue
        count+=1;pending+=1
    return count


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
    return row.user_id==user_id and listing is not None and listing.current_version_id==row.version_id


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
