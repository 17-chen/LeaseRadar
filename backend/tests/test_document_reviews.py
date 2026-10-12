import base64,hashlib,json,io,zipfile,time
from pathlib import Path
import pytest
from sqlalchemy import select,func
from app.db import Session,DocumentReview,Version
from app.document_worker import extract,ExtractionError,process_one
from test_core import client_for


def docx():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>合成条款</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
    return buf.getvalue()


def test_docx_extraction_keeps_table_position():
    r=extract(docx(),'docx');assert '表1 行1' in r[0]['text'] and r[0]['method']=='docx_table'

@pytest.mark.parametrize('data,kind',[(b'bad','pdf'),(b'%PDF-'+b'x'*5000000,'pdf'),(b'bad','docx')])
def test_invalid_size_or_signature_rejected(data,kind):
    with pytest.raises(Exception):extract(data,kind)


def test_pdf_page_limits_and_ocr_are_explicit(monkeypatch):
    import app.document_worker as worker
    monkeypatch.setattr(worker.shutil,'which',lambda n:'/synthetic/'+n)
    def fake(args,folder,deadline):
        if args[0]=='pdfinfo':return 'Pages: 2\nEncrypted: no'
        if args[0]=='pdftotext':return '合成PDF文字' if args[2]=='1' else ''
        if args[0]=='pdftoppm':return ''
        return '合成OCR文字待复核'
    monkeypatch.setattr(worker,'tool',fake)
    r=extract(b'%PDF-synthetic','pdf')
    assert r[0]['method']=='pdf_text' and r[1]['method']=='ocr_review' and r[1]['page']==2
    monkeypatch.setattr(worker,'tool',lambda *a:'Pages: 21\nEncrypted: no')
    with pytest.raises(ExtractionError):extract(b'%PDF-synthetic','pdf')


def test_file_worker_hash_identity_and_repeat(tmp_path):
    for name in ['requests','inputs','results']:(tmp_path/name).mkdir()
    data=docx();digest=hashlib.sha256(data).hexdigest()
    (tmp_path/'inputs'/f'{digest}.docx').write_bytes(data)
    (tmp_path/'requests'/'1.json').write_text(json.dumps({'sha256':digest,'format':'docx'}))
    assert process_one(tmp_path) and not process_one(tmp_path)
    assert json.loads((tmp_path/'results'/'1.json').read_text())['state']=='review'


def test_api_authority_permission_and_no_auto_fields(monkeypatch,tmp_path):
    import app.document_jobs as jobs
    monkeypatch.setattr(jobs,'QUEUE',tmp_path)
    a=client_for('admin');m=client_for('member')
    data={'filename':'合成附件.docx','content_base64':base64.b64encode(docx()).decode()}
    assert m.post('/api/v1/document-reviews',json=data).status_code==403
    r=a.post('/api/v1/document-reviews',json=data);assert r.status_code==200 and r.json()['state']=='queued'
    assert process_one(tmp_path)
    items=a.get('/api/v1/document-reviews').json()['items'];assert items[0]['state']=='review'
    with Session() as db:assert db.scalar(select(func.count()).select_from(Version))==0
    assert a.post('/api/v1/document-reviews',json={**data,'content_base64':'!!!'}).status_code==422
    assert m.get('/api/v1/document-reviews').status_code==403


def test_bad_worker_result_cannot_inject_fields(monkeypatch,tmp_path):
    import app.document_jobs as jobs
    monkeypatch.setattr(jobs,'QUEUE',tmp_path)
    a=client_for('admin');a.post('/api/v1/document-reviews',json={'filename':'合成附件.docx','content_base64':base64.b64encode(docx()).decode()})
    (tmp_path/'results'/'1.json').write_text(json.dumps({'sha256':'wrong','format':'docx','state':'review','pages':[]}))
    assert a.get('/api/v1/document-reviews').json()['items'][0]['state']=='failed'
