"""Synthetic transport only: real DB queue, SSRF guards and isolated review protocol."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import hashlib
import httpx
import pytest
from sqlalchemy import select,func
from app.db import Session,DocumentDownload,DocumentReview,Version,Source,User
import app.document_downloads as downloads
from app.service import ingest
from app.document_worker import process_one
from app.document_jobs import reconcile
from app.collectors import SourceError
from test_core import sample,client_for
from test_document_reviews import body_docx

@pytest.fixture
def download_fixture(monkeypatch,tmp_path):
    import app.service as service
    import app.document_jobs as jobs
    monkeypatch.setattr(jobs,'QUEUE',tmp_path/'queue')
    monkeypatch.setenv('SOURCE_DOCUMENTS_ENABLED','true')
    monkeypatch.setenv('SOURCE_DOCUMENT_DOWNLOADS_ENABLED','true')
    monkeypatch.setenv('SOURCE_DOCUMENTS_USER_ID','1')
    original=service.PARSERS['nongjy']
    def parser(html,url):
        fields,evidence,text=original(html,url)
        fields['attachments']=[{'url':'https://www.nongjy.cn/synthetic.docx'}]
        return fields,evidence,text
    monkeypatch.setitem(service.PARSERS,'nongjy',parser)
    data=body_docx('<w:p><w:r><w:t>合成下载附件，须人工核验</w:t></w:r></w:p>')
    calls=[]
    @contextmanager
    def transport(url):
        calls.append(url)
        yield httpx.Response(200,content=data)
    monkeypatch.setattr(downloads,'stream_public',transport)
    return tmp_path,data,calls


def observe(db,price='120000'):
    return ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample(price))


def due_again():
    with Session() as db:
        for row in db.scalars(select(DocumentDownload).where(DocumentDownload.state=='retry_wait')):row.retry_at='2000-01-01T00:00:00+00:00'
        db.get(Source,'nongjy').lease_until=None;db.commit()


def test_download_ingest_to_review_end_to_end(download_fixture):
    root,data,calls=download_fixture
    with Session() as db:
        observe(db);db.commit();observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentDownload))==1
    downloads.process_download();downloads.process_download()
    assert len(calls)==1
    with Session() as db:
        job=db.scalar(select(DocumentDownload));assert job.state=='downloaded' and job.attempts==1 and job.sha256==hashlib.sha256(data).hexdigest()
        review=db.get(DocumentReview,job.review_id);assert review.origin_version_id==job.version_id and review.origin_url==job.url
        reconcile(db);db.commit()
    assert process_one(root/'queue')
    with Session() as db:
        reconcile(db);db.commit();assert db.scalar(select(DocumentReview)).state=='review'
        assert db.scalar(select(func.count()).select_from(Version))==1
    response=client_for('admin').get('/api/v1/document-downloads').json()
    assert response['total']==1 and response['items'][0]['state']=='downloaded'
    assert 'token' not in response['items'][0]
    assert client_for('member').get('/api/v1/document-downloads').status_code==403


def test_rolled_back_observation_does_not_download(download_fixture):
    root,data,calls=download_fixture
    with Session() as db:observe(db);db.rollback()
    downloads.process_download();assert not calls


@pytest.mark.parametrize('status,state',[(403,'blocked'),(401,'blocked'),(302,'failed'),(404,'failed'),(429,'retry_wait'),(503,'retry_wait')])
def test_http_status_is_preserved_without_redirect_or_bypass(download_fixture,monkeypatch,status,state):
    @contextmanager
    def transport(url):yield httpx.Response(status,headers={'retry-after':'3600','location':'https://127.0.0.1/secret'})
    monkeypatch.setattr(downloads,'stream_public',transport)
    with Session() as db:observe(db);db.commit()
    downloads.process_download()
    with Session() as db:
        row=db.scalar(select(DocumentDownload));assert row.state==state and row.attempts==1 and str(status) in row.error
        if state=='retry_wait':assert datetime.fromisoformat(row.retry_at)>datetime.now(timezone.utc)+timedelta(minutes=59)
        assert db.scalar(select(func.count()).select_from(DocumentReview))==0


@pytest.mark.parametrize('content,headers',[(b'<html>not a docx</html>',{}),(b'PK'+b'x'*5000000,{}),(b'PKsmall',{'content-length':'5000001'}),(b'PKsmall',{'content-length':'invalid'})])
def test_size_and_signature_rejected(download_fixture,monkeypatch,content,headers):
    @contextmanager
    def transport(url):yield httpx.Response(200,content=content,headers=headers)
    monkeypatch.setattr(downloads,'stream_public',transport)
    with Session() as db:observe(db);db.commit()
    downloads.process_download()
    with Session() as db:assert db.scalar(select(DocumentDownload)).state=='failed' and not db.scalar(select(DocumentReview))


def test_three_attempts_then_failure_survives_restart(download_fixture,monkeypatch):
    def error(*args):raise httpx.ConnectError('synthetic connection failure')
    monkeypatch.setattr(downloads,'download',error)
    with Session() as db:observe(db);db.commit()
    for _ in range(3):downloads.process_download();due_again()
    downloads.process_download()
    with Session() as db:
        row=db.scalar(select(DocumentDownload));assert row.attempts==3 and row.state=='failed'


def test_stale_version_cancelled_without_fetch(download_fixture):
    root,data,calls=download_fixture
    with Session() as db:observe(db);db.commit();observe(db,'130000');db.commit()
    downloads.process_download()
    with Session() as db:
        rows=db.scalars(select(DocumentDownload).order_by(DocumentDownload.id)).all()
        assert rows[0].state=='cancelled' and rows[1].state=='downloaded'
    assert len(calls)==1


def test_old_token_cannot_publish_review(download_fixture,monkeypatch):
    root,data,calls=download_fixture
    def stolen(*args):
        with Session() as db:
            row=db.scalar(select(DocumentDownload));row.token='replacement-owner';db.commit()
        return data
    monkeypatch.setattr(downloads,'download',stolen)
    with Session() as db:observe(db);db.commit()
    downloads.process_download()
    with Session() as db:assert not db.scalar(select(DocumentReview))


def test_shared_source_lease_prevents_overlap(download_fixture):
    root,data,calls=download_fixture
    with Session() as db:
        observe(db);db.commit();source=db.get(Source,'nongjy');source.lease_token='crawler';source.lease_until='2099-01-01T00:00:00+00:00';db.commit()
    downloads.process_download();assert not calls
    with Session() as db:assert db.scalar(select(DocumentDownload)).attempts==0


def test_disabled_and_changed_owner_never_redirect_old_jobs(download_fixture,monkeypatch):
    root,data,calls=download_fixture
    with Session() as db:observe(db);db.commit()
    monkeypatch.setenv('SOURCE_DOCUMENT_DOWNLOADS_ENABLED','false')
    downloads.process_download();assert not calls
    with Session() as db:
        other=User(username='secondadmin',password_hash='synthetic',role='admin');db.add(other);db.commit();other_id=other.id
    monkeypatch.setenv('SOURCE_DOCUMENT_DOWNLOADS_ENABLED','true');monkeypatch.setenv('SOURCE_DOCUMENTS_USER_ID',str(other_id))
    downloads.process_download();assert not calls
    with Session() as db:assert db.scalar(select(DocumentDownload)).state=='cancelled'


def test_queue_capacity_defers_then_recovers(download_fixture):
    root,data,calls=download_fixture
    with Session() as db:
        observe(db);db.commit()
        for i in range(20):db.add(DocumentReview(user_id=1,filename=str(i),sha256='a'*64,format='docx'))
        db.commit()
    downloads.process_download();assert not calls
    with Session() as db:
        for row in db.scalars(select(DocumentReview)):row.state='failed'
        db.commit()
    downloads.process_download();assert len(calls)==1


@pytest.mark.parametrize('url',['http://www.nongjy.cn/x.pdf','https://127.0.0.1/x.pdf','https://www.nongjy.cn.evil.test/x.pdf','https://www.nongjy.cn:8080/x.pdf','https://user@www.nongjy.cn/x.pdf'])
def test_invalid_urls_do_not_reach_transport(download_fixture,url):
    root,data,calls=download_fixture
    with pytest.raises(SourceError):downloads.download(url,'pdf')
    assert not calls


def test_rebinding_to_private_address_is_blocked(monkeypatch):
    import app.collectors as collectors
    monkeypatch.setattr(collectors.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(SourceError,match='公网'):downloads.download('https://www.nongjy.cn/x.pdf','pdf')


def test_expired_get_recovers_with_attempt_count(download_fixture):
    with Session() as db:
        observe(db);db.commit();row=db.scalar(select(DocumentDownload))
        row.state='downloading';row.attempts=1;row.token='expired';row.lease_until='2000-01-01T00:00:00+00:00';db.commit()
    downloads.process_download()
    with Session() as db:
        row=db.scalar(select(DocumentDownload));assert row.state=='downloaded' and row.attempts==2


def test_expired_third_attempt_stops(download_fixture):
    root,data,calls=download_fixture
    with Session() as db:
        observe(db);db.commit();row=db.scalar(select(DocumentDownload))
        row.state='downloading';row.attempts=3;row.token='expired';row.lease_until='2000-01-01T00:00:00+00:00';db.commit()
    downloads.process_download();assert not calls
    with Session() as db:assert db.scalar(select(DocumentDownload)).state=='failed'


def test_source_lease_takeover_prevents_late_result(download_fixture,monkeypatch):
    root,data,calls=download_fixture
    def stolen(*args):
        with Session() as db:db.get(Source,'nongjy').lease_token='new-source-owner';db.commit()
        return data
    monkeypatch.setattr(downloads,'download',stolen)
    with Session() as db:observe(db);db.commit()
    downloads.process_download()
    with Session() as db:
        assert not db.scalar(select(DocumentReview))
        assert db.get(Source,'nongjy').lease_token=='new-source-owner'


def test_blocked_address_not_requeued_for_new_version(download_fixture,monkeypatch):
    def blocked(*args):raise SourceError('HTTP 403',blocked=True)
    monkeypatch.setattr(downloads,'download',blocked)
    with Session() as db:observe(db);db.commit()
    downloads.process_download()
    with Session() as db:
        observe(db,'130000');db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentDownload))==1
        assert db.scalar(select(DocumentDownload)).state=='blocked'
