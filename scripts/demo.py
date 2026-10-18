#!/usr/bin/env python3
"""Create a fresh, isolated synthetic competition demo; never reset existing data."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,help='必须是不存在的新目录；默认private/demo-runs下独立目录')
    parser.add_argument('--port',type=int,default=8001)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('端口须为1024–65535')
    data=(args.data_dir or ROOT/'private'/'demo-runs'/uuid.uuid4().hex[:12]).resolve()
    if data.exists():parser.error('拒绝覆盖已有目录；使用新的--data-dir，原演示和失败记录会保留')
    data.mkdir(parents=True,mode=0o700)
    python=ROOT/'.venv'/'bin'/'python'
    if not python.exists():python=Path(sys.executable)
    env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'DATA_DIR':str(data),
         'DATABASE_URL':'sqlite:///'+str(data/'demo.db'),'APP_MODE':'demo','COOKIE_SECURE':'false',
         'EMAIL_ENABLED':'false','SOURCE_ALERT_EMAIL_ENABLED':'false','SOURCE_DOCUMENTS_ENABLED':'false',
         'SOURCE_DOCUMENT_DOWNLOADS_ENABLED':'false','SOURCE_DOCUMENTS_USER_ID':'0','DEMO_PORT':str(args.port)}
    subprocess.run([str(python),'-m','app.demo'],env=env,cwd=ROOT,check=True)
    print(f'合成DEMO：http://127.0.0.1:{args.port}；账号与步骤：{data / "DEMO_GUIDE.md"}',flush=True)
    if not args.prepare_only:
        subprocess.run([str(python),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(args.port)],env=env,cwd=ROOT,check=True)

if __name__=='__main__':main()
