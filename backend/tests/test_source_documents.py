"""No network: synthetic source snapshots exercise the real ingest and review path."""
import hashlib
import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.db import Session,User,DocumentReview,Listing,Version,Event
from app.service import ingest
from app.document_worker import process_one
from app.document_jobs import reconcile
from test_core import sample,client_for
from test_document_reviews import body_docx

@pytest.fixture
def source_fixture(monkeypatch,tmp_path):
    import app.source_documents as source
    import app.document_jobs as jobs
    import app.service as service
    monkeypatch.setattr(source,'DATA',tmp_path)
    monkeypatch.setattr(jobs,'QUEUE',tmp_path/'document_queue')
    data=body_docx('<w:p><w:r><w:t>合成来源附件，不是商业条件确认</w:t></w:r></w:p>')
    digest=hashlib.sha256(data).hexdigest()
    (tmp_path/'snapshots').mkdir()
    (tmp_path/'snapshots'/f'{digest}.docx').write_bytes(data)
    attachments=[{'url':'https://www.nongjy.cn/synthetic.docx','sha256':digest}]
    original=service.PARSERS['nongjy']
    def parser(html,url):
        fields,evidence,text=original(html,url)
        fields['attachments']=list(attachments)
        return fields,evidence,text
    monkeypatch.setitem(service.PARSERS,'nongjy',parser)
    with Session() as db:admin=db.scalar(select(User).where(User.role=='admin')).id
    monkeypatch.setenv('SOURCE_DOCUMENTS_ENABLED','true')
    monkeypatch.setenv('SOURCE_DOCUMENTS_USER_ID',str(admin))
    return tmp_path,attachments,admin


def observe(db,amount='120000'):
    return ingest(db,'nongjy','https://www.nongjy.cn/web/propertyBid/detail/1',sample(amount))


def test_source_snapshot_to_review_idempotent_across_versions(source_fixture):
    root,files,admin=source_fixture
    with Session() as db:
        for amount in ['120000','120000','130000']:observe(db,amount);db.commit()
        rows=db.scalars(select(DocumentReview)).all();assert len(rows)==1
        row=rows[0];assert row.origin_url==files[0]['url'] and row.origin_version_id==1
        assert row.user_id==admin and row.listing_id==1
        reconcile(db);db.commit()
    assert process_one(root/'document_queue')
    with Session() as db:
        reconcile(db);db.commit()
        assert db.get(DocumentReview,1).state=='review'
        assert db.scalar(select(func.count()).select_from(Version))==2
        assert db.scalar(select(func.count()).select_from(Event))==2
    page=client_for('admin').get('/api/v1/document-reviews').json()['items'][0]
    assert page['origin_version_id']==1 and page['origin_url']==files[0]['url']
    assert client_for('member').get('/api/v1/document-reviews').status_code==403


def test_transaction_rollback_never_publishes_requests(source_fixture):
    root,files,admin=source_fixture
    with Session() as db:observe(db);db.rollback()
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(DocumentReview))==0
        reconcile(db);db.commit()
    assert not (root/'document_queue'/'requests'/'1.json').exists()
    assert not process_one(root/'document_queue')


@pytest.mark.parametrize('configuration',['disabled','member','invalid'])
def test_opt_in_requires_valid_admin(source_fixture,monkeypatch,configuration):
    root,files,admin=source_fixture
    if configuration=='disabled':monkeypatch.setenv('SOURCE_DOCUMENTS_ENABLED','false')
    else:monkeypatch.setenv('SOURCE_DOCUMENTS_USER_ID','2' if configuration=='member' else 'bad')
    with Session() as db:
        observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentReview))==0
        assert db.scalar(select(func.count()).select_from(Listing))==1
    state=client_for('admin').get('/api/v1/setup-readiness').json()['source_documents']
    assert state==('disabled' if configuration=='disabled' else 'invalid_configuration')


@pytest.mark.parametrize('failure',['missing','corrupt','symlink','oversize'])
def test_invalid_snapshot_keeps_failure_and_does_not_retry(source_fixture,failure,tmp_path):
    root,files,admin=source_fixture
    path=root/'snapshots'/f"{files[0]['sha256']}.docx"
    path.unlink()
    if failure=='corrupt':path.write_bytes(b'PKcorrupt')
    if failure=='symlink':path.symlink_to(__file__)
    if failure=='oversize':path.write_bytes(b'x'*5000001)
    with Session() as db:
        for _ in range(2):observe(db);db.commit()
        rows=db.scalars(select(DocumentReview)).all()
        assert len(rows)==1 and rows[0].state=='failed' and rows[0].error
        assert rows[0].origin_url==files[0]['url']


def test_unhashed_and_external_metadata_never_read_or_fetched(source_fixture):
    root,files,admin=source_fixture
    files[:]=[{'url':'https://127.0.0.1/private.docx','sha256':'a'*64}, {'url':'https://www.nongjy.cn/x.docx','sha256':'../../secret'}, {'url':'https://www.nongjy.cn/not-cached.pdf'}]
    with Session() as db:
        observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentReview))==0


def test_changed_content_at_same_url_creates_new_review(source_fixture):
    root,files,admin=source_fixture
    with Session() as db:observe(db);db.commit()
    data=body_docx('<w:p><w:r><w:t>合成新的附件内容</w:t></w:r></w:p>')
    digest=hashlib.sha256(data).hexdigest()
    (root/'snapshots'/f'{digest}.docx').write_bytes(data);files[0]={**files[0],'sha256':digest}
    with Session() as db:
        observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentReview))==2


def test_backpressure_recovers_on_unchanged_observation(source_fixture):
    root,files,admin=source_fixture
    with Session() as db:
        for i in range(20):db.add(DocumentReview(user_id=admin,filename=f'pending{i}',sha256='b'*64,format='docx'))
        db.commit();observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentReview))==20
        for r in db.scalars(select(DocumentReview)):r.state='review'
        db.commit();observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentReview))==21


def test_origin_unique_key_is_database_authority(source_fixture):
    root,files,admin=source_fixture
    with Session() as db:
        observe(db);db.commit();row=db.scalar(select(DocumentReview))
        db.add(DocumentReview(user_id=admin,listing_id=row.listing_id,filename='duplicate',sha256=row.sha256,format='docx',origin_url=row.origin_url,origin_version_id=row.origin_version_id))
        with pytest.raises(IntegrityError):db.commit()


def test_one_observation_bounded_to_five_reviews(source_fixture):
    root,files,admin=source_fixture
    original=files[0]
    files[:]=[{**original,'url':f'https://www.nongjy.cn/synthetic-{i}.docx'} for i in range(8)]
    with Session() as db:
        observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentReview))==5
        observe(db);db.commit()
        assert db.scalar(select(func.count()).select_from(DocumentReview))==8
