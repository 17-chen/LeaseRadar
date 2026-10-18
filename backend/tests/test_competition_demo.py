"""Fresh-process demo checks: no network, no live DB, no overwrite."""
import os,subprocess,sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]

def environment(path):
    return {**os.environ,'PYTHONPATH':str(ROOT/'backend'),'DATA_DIR':str(path),'DATABASE_URL':'sqlite:///'+str(path/'demo.db'),
            'APP_MODE':'demo','EMAIL_ENABLED':'false','SOURCE_ALERT_EMAIL_ENABLED':'false','SOURCE_DOCUMENTS_ENABLED':'false','SOURCE_DOCUMENT_DOWNLOADS_ENABLED':'false'}


def test_storyline_and_authenticated_workflows_without_network(tmp_path):
    script='''
import socket,re
# Any accidental source/SMTP GET fails this test.
def forbidden(*a,**k):raise AssertionError('DEMO attempted real network')
socket.socket.connect=forbidden
from app.demo import prepare
from app.config import DATA
summary=prepare()
assert summary['listings']==6 and summary['versions']==7 and summary['inbox']==5
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
password=re.search(r'密码：([^\\n]+)',(DATA/'DEMO_GUIDE.md').read_text()).group(1)
r=client.post('/api/v1/auth/login',json={'username':'demo','password':password});assert r.status_code==200
client.headers['X-CSRF-Token']=r.json()['csrf']
assert client.get('/api/v1/auth/me').json()['mode']=='demo'
r=client.post('/api/v1/listings/search',json={'filters':{'area_m2_min':'30','first_year_monthly_max':'12000','registration_open':True}})
assert r.status_code==200 and r.json()['total']==4
r=client.post('/api/v1/comparisons',json={'listing_ids':[1,2,6]});assert r.status_code==200
assert client.get('/api/v1/document-downloads').json()['items'][0]['state']=='blocked'
try:prepare()
except ValueError:pass
else:raise AssertionError('Existing demo must not be overwritten')
from app.db import Session,Listing
from sqlalchemy import select,func
with Session() as db:assert db.scalar(select(func.count()).select_from(Listing))==6
'''
    result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=environment(tmp_path),capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('override',[{'APP_MODE':'live'},{'EMAIL_ENABLED':'true'},{'SOURCE_DOCUMENT_DOWNLOADS_ENABLED':'true'}])
def test_prepare_refuses_live_or_external_configuration(tmp_path,override):
    result=subprocess.run([sys.executable,'-m','app.demo'],cwd=ROOT,env={**environment(tmp_path),**override},capture_output=True,text=True,timeout=30)
    assert result.returncode!=0
    assert not (tmp_path/'DEMO_GUIDE.md').exists()


def test_launcher_overrides_inherited_database_and_preserves_existing_folder(tmp_path):
    live=tmp_path/'live.db';live.write_text('synthetic sentinel: must never touch')
    fresh=tmp_path/'new-demo'
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(live),'EMAIL_ENABLED':'true'}
    command=[sys.executable,str(ROOT/'scripts/demo.py'),'--prepare-only','--data-dir',str(fresh)]
    first=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
    assert first.returncode==0,first.stdout+first.stderr
    assert live.read_text()=='synthetic sentinel: must never touch'
    assert (fresh/'demo.db').exists() and (fresh/'DEMO_GUIDE.md').exists()
    again=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert again.returncode!=0 and '拒绝覆盖' in again.stderr
