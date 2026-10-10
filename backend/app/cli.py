import argparse
import getpass
import json
from pathlib import Path
from argon2 import PasswordHasher
from sqlalchemy import select
from .db import Session, User, seed_sources
from .config import ROOT

def main():
    parser = argparse.ArgumentParser(prog='leaseradar')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('migrate')
    sub.add_parser('backup')
    admin = sub.add_parser('create-admin'); admin.add_argument('--username', default='admin')
    crawl = sub.add_parser('crawl-once'); crawl.add_argument('source', choices=['nongjy', 'wzpt']); crawl.add_argument('--pages', type=int, default=1)
    check = sub.add_parser('source-check'); check.add_argument('source', choices=['nongjy', 'wzpt'])
    ingest = sub.add_parser('import-html'); ingest.add_argument('source', choices=['nongjy', 'wzpt']); ingest.add_argument('path'); ingest.add_argument('--url', required=True)
    args = parser.parse_args()
    if args.command == 'migrate':
        from alembic import command
        from alembic.config import Config
        config = Config(str(ROOT / 'backend' / 'alembic.ini'))
        command.upgrade(config, 'head')
        with Session() as db: seed_sources(db)
    elif args.command == 'backup':
        from .config import DATABASE_URL, DATA
        if not DATABASE_URL.startswith('sqlite:///'): parser.error('PostgreSQL备份请使用docs/DEPLOYMENT.md中的pg_dump流程')
        import sqlite3, shutil
        from datetime import datetime, timezone
        folder = DATA / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        folder.mkdir(parents=True)
        with sqlite3.connect(DATABASE_URL.removeprefix('sqlite:///')) as original, sqlite3.connect(folder / 'database.db') as backup:
            original.backup(backup)
        if (DATA / 'snapshots').exists(): shutil.copytree(DATA / 'snapshots', folder / 'snapshots')
        print(f'备份写入 {folder}；包含私有数据，不入Git')
    elif args.command == 'create-admin':
        password = getpass.getpass('Password (12+ characters): ')
        if len(password) < 12: parser.error('密码至少12位')
        if password != getpass.getpass('Confirm password: '): parser.error('密码不一致')
        with Session() as db:
            if db.scalar(select(User).where(User.username == args.username)): parser.error('用户已存在；不覆盖')
            db.add(User(username=args.username, password_hash=PasswordHasher().hash(password), role='admin')); db.commit()
        print('管理员已创建')
    elif args.command == 'crawl-once':
        if not 1 <= args.pages <= 150: parser.error('页数须为1–150')
        from .service import crawl, deliver_local
        print(json.dumps(crawl(args.source, args.pages), ensure_ascii=False)); deliver_local()
    elif args.command == 'source-check':
        from .collectors import fetch, DISCOVERERS
        from .db import Source
        with Session() as db: source = db.get(Source, args.source); url = source.seed_url
        refs, pages = DISCOVERERS[args.source](fetch(url))
        print(json.dumps({'detail_count': len(refs), 'pages': pages, 'sample': refs[:5]}, ensure_ascii=False))
    elif args.command == 'import-html':
        from .service import ingest, deliver_local
        from .collectors import validate_url
        validate_url(args.url)
        with Session() as db:
            result = ingest(db, args.source, args.url, Path(args.path).read_text()); db.commit()
        print(result); deliver_local()

if __name__ == '__main__': main()
