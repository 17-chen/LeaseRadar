"""Prove uploaded files and queue results survive a different DATA_DIR."""
import os,subprocess,sys
from pathlib import Path


def test_backup_includes_document_inputs_and_results(tmp_path):
    root=Path(__file__).resolve().parents[2]
    env={**os.environ,'PYTHONPATH':str(root/'backend'),'DATA_DIR':str(tmp_path/'original'),
         'DATABASE_URL':'sqlite:///'+str(tmp_path/'original'/'db.sqlite'),'APP_MODE':'demo','EMAIL_ENABLED':'false'}
    script='''
import io,zipfile,hashlib,shutil,os
from pathlib import Path
from app.cli import main
from app.db import Session,User,DocumentReview
from app.document_jobs import upload,reconcile
from app.document_worker import process_one
import sys
sys.argv=['leaseradar','migrate'];main()
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:tbl><w:tr><w:tc><w:p><w:r><w:t>synthetic evidence</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:document>')
import base64
with Session() as db:
 user=User(username='synthetic',password_hash='synthetic',role='admin');db.add(user);db.flush()
 row=upload(db,user.id,None,'synthetic.docx',base64.b64encode(buffer.getvalue()).decode());db.commit();reconcile(db);db.commit()
from app.config import DATA
assert process_one(DATA/'document_queue')
with Session() as db:reconcile(db);db.commit();assert db.get(DocumentReview,1).state=='review'
sys.argv=['leaseradar','backup'];main()
backup=next((DATA/'backups').iterdir())
assert (backup/'document_queue'/'inputs').is_dir() and (backup/'document_queue'/'results'/'1.json').exists()
restored=DATA.parent/'restored';shutil.copytree(backup,restored)
assert hashlib.sha256(next((restored/'document_queue'/'inputs').glob('*.docx')).read_bytes()).hexdigest()==hashlib.sha256(buffer.getvalue()).hexdigest()
import sqlite3
c=sqlite3.connect(restored/'database.db');assert c.execute('select state from document_reviews').fetchone()[0]=='review'
assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
'''
    result=subprocess.run([sys.executable,'-c',script],cwd=root,env=env,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
