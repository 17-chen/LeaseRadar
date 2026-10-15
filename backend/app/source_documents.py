"""Opt-in review of already downloaded source snapshots; never fetch arbitrary URLs."""
import base64
import hashlib
import os
import re
from urllib.parse import urlsplit
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from .config import DATA
from .db import DocumentReview,User
from .document_jobs import upload


def configuration(db):
    if os.getenv('SOURCE_DOCUMENTS_ENABLED','false').lower()!='true':return None
    try:user_id=int(os.getenv('SOURCE_DOCUMENTS_USER_ID','0'))
    except ValueError:raise ValueError('来源附件审核管理员ID无效')
    user=db.get(User,user_id)
    if not user or user.role!='admin':raise ValueError('来源附件审核须指定有效管理员')
    return user.id


def enqueue_cached(db,version):
    """At most five new reviews per observation, twenty pending per owner.

    The enclosing ingestion transaction owns the reviews. Files may precede commit,
    but requests are only published later by the DB reconciler.
    """
    try:user_id=configuration(db)
    except ValueError:return {'queued':0,'failed':0,'configuration':'invalid'}
    if user_id is None:return {'queued':0,'failed':0,'configuration':'disabled'}
    counts={'queued':0,'failed':0,'configuration':'configured'}
    pending=db.scalar(select(func.count()).select_from(DocumentReview).where(DocumentReview.user_id==user_id,DocumentReview.state=='queued'))
    attachments=version.fields.get('attachments',[])
    if not isinstance(attachments,list):return counts
    for attachment in attachments[:20]:
        if counts['queued']+counts['failed']>=5 or pending>=20:break
        if not isinstance(attachment,dict):continue
        digest=attachment.get('sha256');url=attachment.get('url')
        if not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest) or not isinstance(url,str) or len(url)>2000:continue
        try:parsed=urlsplit(url)
        except ValueError:continue
        # Stored metadata is not permission to fetch. This path only reads local
        # hash-named snapshots that the existing source downloader already saved.
        suffix='docx' if parsed.path.lower().endswith('.docx') else 'pdf' if parsed.path.lower().endswith('.pdf') else None
        if parsed.scheme!='https' or parsed.hostname not in ('www.nongjy.cn','www.wzpt.edu.cn','www.wzcqpt.com') or parsed.username or parsed.password or suffix is None:continue
        existing=db.scalar(select(DocumentReview.id).where(DocumentReview.listing_id==version.listing_id,DocumentReview.origin_url==url,DocumentReview.sha256==digest))
        if existing:continue
        path=DATA/'snapshots'/f'{digest}.{suffix}'
        error=None;data=None
        try:
            if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=5_000_000:raise ValueError('来源附件缺失或超过5MB边界')
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('来源附件哈希不一致')
            if not (data.startswith(b'%PDF-') if suffix=='pdf' else data.startswith(b'PK')):raise ValueError('来源附件签名不一致')
        except (OSError,ValueError) as exc:error=str(exc)[:200]
        try:
            with db.begin_nested():
                filename=f'来源附件-{digest[:12]}.{suffix}'
                if error:
                    row=DocumentReview(user_id=user_id,listing_id=version.listing_id,filename=filename,sha256=digest,format=suffix,state='failed',error=error)
                    db.add(row)
                else:row=upload(db,user_id,version.listing_id,filename,base64.b64encode(data).decode())
                row.origin_version_id=version.id;row.origin_url=url
                db.flush()
        except IntegrityError:
            # A concurrent observer may have inserted the same origin/content.
            # The unique key is authoritative; never roll back the parent ingest.
            continue
        counts['failed' if error else 'queued']+=1
        if not error:pending+=1
    return counts
