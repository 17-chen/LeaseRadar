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


def body_docx(content):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+content+'</w:body></w:document>')
    return buf.getvalue()


def test_docx_body_and_tables_keep_order_without_deleted_text():
    data=body_docx('<w:p><w:r><w:t>租金</w:t><w:tab/><w:t>每年递增</w:t><w:br/><w:t>待核验</w:t></w:r><w:del><w:r><w:t>旧金额</w:t></w:r></w:del></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>表内依据</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:r><w:t>免租须确认</w:t></w:r></w:p>')
    page=extract(data,'docx')[0]
    assert page['method']=='docx_text' and page['page'] is None
    assert page['text']=='正文段1：租金\t每年递增\n待核验\n表1 行1：表内依据\n正文段2：免租须确认'


def test_body_only_document_reaches_review_without_business_updates(monkeypatch,tmp_path):
    import app.document_jobs as jobs
    monkeypatch.setattr(jobs,'QUEUE',tmp_path)
    a=client_for('admin')
    data=body_docx('<w:p><w:r><w:t>合成正文：租金周期未说明</w:t></w:r></w:p>')
    response=a.post('/api/v1/document-reviews',json={'filename':'正文.docx','content_base64':base64.b64encode(data).decode()})
    assert response.status_code==200
    assert process_one(tmp_path)
    row=a.get('/api/v1/document-reviews').json()['items'][0]
    assert row['state']=='review' and row['pages'][0]['method']=='docx_text'
    with Session() as db:assert db.scalar(select(func.count()).select_from(Version))==0


@pytest.mark.parametrize('content',['<w:p/>','<w:p><w:r><w:t>'+('字'*100001)+'</w:t></w:r></w:p>'])
def test_docx_empty_or_excessive_body_is_not_success(content):
    with pytest.raises(Exception):extract(body_docx(content),'docx')


def test_utf16_entity_declaration_and_duplicate_body_rejected():
    buf=io.BytesIO()
    xml='<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY v "bad">]><x>&v;</x>'
    with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml',xml.encode('utf-16'))
    with pytest.raises(Exception,match='实体'):extract(buf.getvalue(),'docx')
    with zipfile.ZipFile(buf,'a') as z:
        with pytest.warns(UserWarning):z.writestr('word/document.xml','<x/>')
    with pytest.raises(Exception,match='重复'):extract(buf.getvalue(),'docx')


@pytest.mark.parametrize('bad',[b'{broken',b'[]',b'{"sha256":42,"format":"docx"}',b'x'*1001])
def test_poison_request_preserved_and_next_document_processed(tmp_path,bad):
    for name in ['requests','inputs','results']:(tmp_path/name).mkdir()
    (tmp_path/'requests'/'1.json').write_bytes(bad)
    data=docx();digest=hashlib.sha256(data).hexdigest()
    (tmp_path/'inputs'/f'{digest}.docx').write_bytes(data)
    (tmp_path/'requests'/'2.json').write_text(json.dumps({'sha256':digest,'format':'docx'}))
    assert process_one(tmp_path)
    assert json.loads((tmp_path/'results'/'1.json').read_text())['state']=='failed'
    assert (tmp_path/'requests'/'1.json').read_bytes()==bad
    assert process_one(tmp_path)
    assert json.loads((tmp_path/'results'/'2.json').read_text())['state']=='review'
    assert not process_one(tmp_path)
