"""Prove the outbox migration preserves existing events and recipient records."""
import os
from pathlib import Path
import subprocess
import sys

def test_upgrade_populated_0003_database(tmp_path):
    root=Path(__file__).resolve().parents[2]
    env={**os.environ,'DATA_DIR':str(tmp_path),'DATABASE_URL':'sqlite:///'+str(tmp_path/'old.db'),'APP_MODE':'demo','PYTHONPATH':str(root/'backend')}
    script=r'''
from alembic import command
from alembic.config import Config
from app.db import engine,Session,Subscription,Outbox,Source,EmailDelivery
from sqlalchemy import text
cfg=Config('backend/alembic.ini')
command.upgrade(cfg,'0003')
with engine.begin() as connection:
    for statement in [
        "INSERT INTO users VALUES (1,'synthetic','synthetic-hash','member')",
        "INSERT INTO sources (id,name,seed_url,enabled,status,backfill_page) VALUES ('nongjy','synthetic','https://www.nongjy.cn/web/propertyBid/list',0,'partial',2)",
        "INSERT INTO assets VALUES (1,'synthetic address')",
        "INSERT INTO listing_rounds VALUES (1,1,'2026-10-10T00:00:00+00:00',1)",
        "INSERT INTO raw_documents VALUES (1,'https://www.nongjy.cn/web/propertyBid/detail/1','2026-10-10T00:00:00+00:00','synthetic','synthetic text','synthetic.html')",
        "INSERT INTO listing_versions VALUES (1,1,1,'2026-10-10T00:00:00+00:00','synthetic','{}',NULL,NULL)",
        "INSERT INTO subscriptions VALUES (1,1,'synthetic','{}','review_digest',1,'2026-10-10T00:00:00+00:00')",
        "INSERT INTO change_events VALUES (1,1,'new')",
        "INSERT INTO notification_outbox VALUES (1,1,1,'in_app','accepted','{}','2026-10-10T00:00:00+00:00',0)",
    ]: connection.execute(text(statement))
with engine.begin() as connection:
    connection.execute(text('UPDATE raw_documents SET sha256=:sha,snapshot_path=:path WHERE id=1'), {'sha':'a'*64,'path':'/old/private/snapshots/'+'a'*64+'.html'})
command.upgrade(cfg,'0008')
with engine.begin() as connection:
    connection.execute(text("INSERT INTO email_deliveries (id,outbox_id,recipient,state,attempts,accepted_at) VALUES (1,1,'synthetic@example.test','accepted',1,'2026-10-10T01:00:00+00:00')"))
command.upgrade(cfg,'0009')
with engine.begin() as connection:
    connection.execute(text("INSERT INTO document_reviews (id,user_id,listing_id,filename,sha256,format,state,pages,created_at) VALUES (1,1,1,'synthetic.docx','synthetic','docx','review','[]','2026-10-10T00:00:00+00:00')"))
command.upgrade(cfg,'head')
with Session() as db:
    assert db.execute(text('SELECT snapshot_path FROM raw_documents WHERE id=1')).scalar()=='snapshots/'+'a'*64+'.html'
    assert db.get(Subscription,1).reminder_hours==[72,24]
    assert db.get(Outbox,1).event_id==1 and db.get(Outbox,1).reminder_id is None
    assert db.get(Outbox,1).state=='accepted'
    receipt=db.get(EmailDelivery,1)
    assert receipt.state=='accepted' and receipt.attempts==1 and receipt.manual_retry is False
    assert receipt.message_id is None and receipt.sender_address is None
    assert db.get(Source,'nongjy').backfill_page==2 and db.get(Source,'nongjy').detail_checked==0
    assert db.execute(text('SELECT origin_url,origin_version_id,state FROM document_reviews WHERE id=1')).one()==(None,None,'review')
    assert db.execute(text('PRAGMA integrity_check')).scalar()=='ok'
    assert db.execute(text('PRAGMA foreign_key_check')).all()==[]
'''
    result=subprocess.run([sys.executable,'-c',script],cwd=root,env=env,capture_output=True,text=True,timeout=60)
    assert result.returncode==0, result.stdout+result.stderr
