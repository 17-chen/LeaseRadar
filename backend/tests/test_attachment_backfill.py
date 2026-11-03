"""Historical queue planning: no network or real documents/recipients."""
import json
import os
from unittest.mock import patch
import pytest
from sqlalchemy import select,func
from app.db import Session,DocumentDownload,Version,Listing,SourceRecord
from app.service import ingest
from app.document_downloads import backfill_downloads
from test_core import sample
from test_document_downloads import download_fixture


def historical(db,identity=1,files=1):
    # These records predate opt-in downloading; ingestion must not seed a job.
    with patch.dict(os.environ,{'SOURCE_DOCUMENT_DOWNLOADS_ENABLED':'false'}):
        listing_id,_=ingest(db,'nongjy',f'https://www.nongjy.cn/web/propertyBid/detail/{identity}',sample())
    version=db.get(Version,db.get(Listing,listing_id).current_version_id)
    version.fields={**version.fields,'attachments':[{'url':f'https://www.nongjy.cn/history-{identity}-{i}.docx'} for i in range(files)]}
    db.flush()
    return listing_id,version.id


def test_preview_then_apply_survives_session_restart_and_is_idempotent(download_fixture):
    _,_,calls=download_fixture
    with Session() as db:
        listing,version=historical(db);db.commit()
        result=backfill_downloads(db,'nongjy')
        assert result['planned']==1 and result['queued']==0 and result['stop']=='complete'
        assert not db.scalar(select(DocumentDownload))
        result=backfill_downloads(db,'nongjy',apply=True);db.commit()
        assert result['queued']==1 and result['next_after_listing']==listing
    with Session() as db:
        assert backfill_downloads(db,'nongjy',apply=True)['queued']==0
        assert db.scalar(select(func.count()).select_from(DocumentDownload))==1
        assert db.scalar(select(func.count()).select_from(Version))==1
    assert not calls


def test_partial_listing_keeps_cursor_until_all_candidates_queued(download_fixture):
    with Session() as db:
        listing,_=historical(db,files=7);db.commit()
        first=backfill_downloads(db,'nongjy',apply=True);db.commit()
        assert first['queued']==5 and first['next_after_listing']==0
        assert first['stop']=='listing_limit' and first['has_more']
        second=backfill_downloads(db,'nongjy',after_listing=first['next_after_listing'],apply=True);db.commit()
        assert second['queued']==2 and second['next_after_listing']==listing
        assert not second['has_more']


def test_capacity_never_skips_partial_listing_and_can_resume(download_fixture):
    with Session() as db:
        listing,version=historical(db,files=3)
        for i in range(19):db.add(DocumentDownload(version_id=version,source_id='nongjy',user_id=1,url=f'https://www.nongjy.cn/pending-{i}.pdf',format='pdf'))
        db.commit()
        preview=backfill_downloads(db,'nongjy')
        assert preview['planned']==1 and preview['stop']=='queue_capacity' and preview['next_after_listing']==0
        result=backfill_downloads(db,'nongjy',apply=True);db.commit()
        assert result['queued']==1 and result['next_after_listing']==0
        assert backfill_downloads(db,'nongjy',apply=True)['queued']==0
        for row in db.scalars(select(DocumentDownload)):row.state='downloaded'
        db.commit()
    with Session() as db:
        result=backfill_downloads(db,'nongjy',apply=True);db.commit()
        assert result['queued']==2 and result['next_after_listing']==listing


def test_batch_cursor_and_source_filter_ignore_duplicate_records(download_fixture):
    with Session() as db:
        first,_=historical(db,1);second,_=historical(db,2)
        db.add(SourceRecord(source_id='nongjy',record_id='duplicate-synthetic',lot_code='2',listing_id=first,url='https://www.nongjy.cn/web/propertyBid/detail/1'))
        db.commit()
        assert backfill_downloads(db,'wzpt',apply=True)['scanned']==0
        one=backfill_downloads(db,'nongjy',limit=1,apply=True);db.commit()
        assert one['queued']==1 and one['next_after_listing']==first and one['has_more']
        two=backfill_downloads(db,'nongjy',after_listing=first,limit=1,apply=True);db.commit()
        assert two['queued']==1 and two['next_after_listing']==second and not two['has_more']


def test_uses_current_version_and_preserves_blocked_and_failed_jobs(download_fixture):
    with Session() as db:
        listing,old=historical(db,files=3)
        newer=Version(listing_id=listing,raw_id=db.get(Version,old).raw_id,business_hash='synthetic-new',fields={'attachments':[{'url':'https://www.nongjy.cn/blocked.pdf'},{'url':'https://www.nongjy.cn/failed.pdf'},{'url':'https://www.nongjy.cn/current.pdf'}]})
        db.add(newer);db.flush();db.get(Listing,listing).current_version_id=newer.id
        db.add(DocumentDownload(version_id=old,source_id='nongjy',user_id=1,url='https://www.nongjy.cn/blocked.pdf',format='pdf',state='blocked',error='synthetic HTTP 403'))
        db.add(DocumentDownload(version_id=newer.id,source_id='nongjy',user_id=1,url='https://www.nongjy.cn/failed.pdf',format='pdf',state='failed',attempts=3))
        db.commit()
        result=backfill_downloads(db,'nongjy',apply=True);db.commit()
        assert result['queued']==1
        rows=db.scalars(select(DocumentDownload).order_by(DocumentDownload.id)).all()
        assert [r.state for r in rows]==['blocked','failed','queued']
        assert rows[-1].url.endswith('/current.pdf') and rows[-1].version_id==newer.id


def test_malformed_cached_and_unsafe_metadata_not_queued(download_fixture):
    with Session() as db:
        listing,version_id=historical(db)
        version=db.get(Version,version_id)
        version.fields={'attachments':[None,{'url':[]},{'url':'https://127.0.0.1/private.pdf'},{'url':'https://www.nongjy.cn/x.pdf','sha256':'a'*64},{'url':'https://www.nongjy.cn/ok.pdf'},{'url':'https://www.nongjy.cn/ok.pdf'}]}
        db.commit()
        assert backfill_downloads(db,'nongjy')['planned']==1
        assert backfill_downloads(db,'nongjy',apply=True)['queued']==1
        db.rollback()
        assert not db.scalar(select(DocumentDownload))


@pytest.mark.parametrize('setting,value',[('SOURCE_DOCUMENT_DOWNLOADS_ENABLED','false'),('SOURCE_DOCUMENTS_ENABLED','false'),('SOURCE_DOCUMENTS_USER_ID','2'),('SOURCE_DOCUMENTS_USER_ID','invalid')])
def test_requires_explicit_configuration_and_valid_admin(download_fixture,monkeypatch,setting,value):
    monkeypatch.setenv(setting,value)
    with Session() as db:
        with pytest.raises(ValueError):backfill_downloads(db,'nongjy',apply=True)
        assert not db.scalar(select(DocumentDownload))


@pytest.mark.parametrize('source,cursor,limit',[('unknown',0,25),('nongjy',-1,25),('nongjy',0,0),('nongjy',0,101)])
def test_bounds_rejected(download_fixture,source,cursor,limit):
    with Session() as db:
        with pytest.raises(ValueError):backfill_downloads(db,source,cursor,limit,True)


def test_cli_defaults_to_preview_and_apply_commits(download_fixture,monkeypatch,capsys):
    from app.cli import main
    with Session() as db:historical(db);db.commit()
    monkeypatch.setattr('sys.argv',['leaseradar','backfill-attachments','nongjy','--limit','1'])
    main();preview=json.loads(capsys.readouterr().out)
    assert preview['mode']=='preview' and preview['queued']==0
    with Session() as db:assert not db.scalar(select(DocumentDownload))
    monkeypatch.setattr('sys.argv',['leaseradar','backfill-attachments','nongjy','--apply'])
    main();assert json.loads(capsys.readouterr().out)['queued']==1
    with Session() as db:assert db.scalar(select(DocumentDownload)).state=='queued'


def test_backfilled_job_reaches_private_review_without_new_business_version(download_fixture):
    from app.document_downloads import process_download
    from app.document_jobs import reconcile
    from app.document_worker import process_one
    from app.db import DocumentReview
    root,_,calls=download_fixture
    with Session() as db:
        _,version=historical(db)
        db.commit()
        assert backfill_downloads(db,'nongjy',apply=True)['queued']==1
        db.commit()
    process_download()
    with Session() as db:
        download=db.scalar(select(DocumentDownload))
        assert download.state=='downloaded' and download.version_id==version
        assert db.scalar(select(func.count()).select_from(Version))==1
        reconcile(db);db.commit()
    assert len(calls)==1 and process_one(root/'queue')
    with Session() as db:
        reconcile(db);db.commit()
        review=db.scalar(select(DocumentReview))
        assert review.state=='review' and review.origin_version_id==version
        assert db.scalar(select(func.count()).select_from(Version))==1


def test_attachment_inspection_budget_is_twenty_metadata_items(download_fixture):
    with Session() as db:
        _,version_id=historical(db,files=21);db.commit()
        queued=0
        for _ in range(4):
            result=backfill_downloads(db,'nongjy',apply=True);db.commit();queued+=result['queued']
        assert queued==20 and not result['has_more']
        assert not db.scalar(select(DocumentDownload).where(DocumentDownload.url.endswith('-20.docx')))
