"""Database authority for private attachment reviews; file worker has no credentials."""
import base64,hashlib,json
from sqlalchemy import select
from .config import DATA
from .db import DocumentReview,Session
QUEUE=DATA/'document_queue'

def validate_pages(pages,format):
    if not isinstance(pages,list) or not 1<=len(pages)<=20:raise ValueError('结果页数无效')
    if format=='docx' and len(pages)!=1:raise ValueError('DOCX结果结构无效')
    for index,page in enumerate(pages,1):
        if not isinstance(page,dict) or not isinstance(page.get('text'),str) or not page['text'].strip():
            raise ValueError('结果正文为空或结构无效')
        if len(page['text'])>(20000 if format=='pdf' else 100000):raise ValueError('结果正文超限')
        if format=='pdf':
            if type(page.get('page')) is not int or page['page']!=index or page.get('method') not in ('pdf_text','ocr_review'):
                raise ValueError('PDF页码或提取方式无效')
        elif page.get('page') is not None or page.get('method') not in ('docx_table','docx_text'):
            raise ValueError('DOCX定位或提取方式无效')
    return pages

def upload(db,user_id,listing_id,filename,encoded):
    try:data=base64.b64decode(encoded,validate=True)
    except ValueError:raise ValueError('附件编码无效')
    if not 0<len(data)<=5000000:raise ValueError('附件大小须为1字节至5MB')
    format='pdf' if data.startswith(b'%PDF-') else 'docx' if data.startswith(b'PK') else None
    if format is None:raise ValueError('只支持PDF或DOCX格式签名')
    digest=hashlib.sha256(data).hexdigest()
    for directory in ('requests','inputs','results'):(QUEUE/directory).mkdir(parents=True,exist_ok=True)
    target=QUEUE/'inputs'/f'{digest}.{format}'
    if not target.exists():
        import secrets
        temporary=target.with_suffix('.'+secrets.token_hex(8)+'.tmp');temporary.write_bytes(data);temporary.replace(target)
    row=DocumentReview(user_id=user_id,listing_id=listing_id,filename=filename,sha256=digest,format=format)
    db.add(row);db.flush()
    # Request is published by the queue reconciler only after DB commit.
    return row


def reconcile(db):
    for row in db.scalars(select(DocumentReview).where(DocumentReview.state=='queued')):
        request=QUEUE/'requests'/f'{row.id}.json'
        if not request.exists():
            request.parent.mkdir(parents=True,exist_ok=True)
            temp=request.with_suffix('.tmp');temp.write_text(json.dumps({'sha256':row.sha256,'format':row.format}));temp.replace(request)
        result=QUEUE/'results'/f'{row.id}.json'
        if not result.exists():continue
        try:
            if result.is_symlink() or result.stat().st_size>2000000:raise ValueError('结果文件超过边界')
            payload=json.loads(result.read_text())
            if not isinstance(payload,dict):raise ValueError('结果不是对象')
            if payload.get('sha256')!=row.sha256 or payload.get('format')!=row.format or payload.get('state') not in ('review','failed'):raise ValueError('结果身份或状态不一致')
            pages=validate_pages(payload.get('pages'),row.format) if payload['state']=='review' else []
            row.pages=pages;row.state=payload['state'];row.error=str(payload.get('error') or '')[:200] or None
            if row.state=='failed' and not row.error:row.error='提取失败，需要人工复核'
        except (ValueError,TypeError,OSError):row.state='failed';row.pages=[];row.error='提取结果校验失败，需要人工复核'
