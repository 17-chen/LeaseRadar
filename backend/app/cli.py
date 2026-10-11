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
    sub.add_parser('readiness-check')
    sub.add_parser('digest-once')
    replay=sub.add_parser('replay');replay.add_argument('manifest')
    evaluation=sub.add_parser('evaluate'); evaluation.add_argument('path'); evaluation.add_argument('--output',required=True)
    admin = sub.add_parser('create-admin'); admin.add_argument('--username', default='admin')
    crawl = sub.add_parser('crawl-once'); crawl.add_argument('source', choices=['nongjy', 'wzpt']); crawl.add_argument('--pages', type=int, default=1); crawl.add_argument('--backfill', action='store_true')
    details = sub.add_parser('refresh-details'); details.add_argument('source', choices=['nongjy', 'wzpt']); details.add_argument('--limit', type=int, default=5)
    sub.add_parser('remind-once')
    sub.add_parser('email-once')
    check = sub.add_parser('source-check'); check.add_argument('source', choices=['nongjy', 'wzpt'])
    ingest = sub.add_parser('import-html'); ingest.add_argument('source', choices=['nongjy', 'wzpt']); ingest.add_argument('path'); ingest.add_argument('--url', required=True); ingest.add_argument('--observed-at', required=True, help='原抓取时间，带时区ISO格式；离线回放不冒充新核验')
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
    elif args.command == 'replay':
        from .config import MODE
        from .db import Listing
        from .service import ingest,deliver_local
        if MODE!='demo':parser.error('replay只允许明确的demo环境与独立空数据库')
        manifest_path=Path(args.manifest).resolve()
        manifest=json.loads(manifest_path.read_text())
        if manifest.get('mode')!='demo' or not 1 <= len(manifest.get('records',[])) <= 20:parser.error('manifest必须标记demo，记录限1–20')
        with Session() as db:
            if db.scalar(select(Listing.id).limit(1)):parser.error('replay拒绝写入已有挂牌的数据库，请指定独立空DATA_DIR')
            for item in manifest['records']:
                path=(manifest_path.parent/item['path']).resolve()
                if not path.is_relative_to(manifest_path.parent) or path.stat().st_size>2000000:parser.error('fixture路径或大小无效')
                ingest(db,item['source'],item['url'],path.read_text(),observed_at=item['observed_at'],event_kind='reprocessing')
            db.commit()
        print('DEMO回放完成；不是实时采集，不进入真实试用数据')
    elif args.command == 'evaluate':
        from .evaluation import evaluate
        rows=[json.loads(line) for line in Path(args.path).read_text().splitlines() if line.strip()]
        Path(args.output).write_text(json.dumps(evaluate(rows),ensure_ascii=False,indent=2))
        print('评测结果已写入指定路径；不代表真实试用效果')
    elif args.command == 'readiness-check':
        from .readiness import inventory
        with Session() as db: print(json.dumps(inventory(db),ensure_ascii=False,indent=2))
    elif args.command == 'digest-once':
        from .scheduling import dispatch_local
        print(json.dumps({'digest_users':dispatch_local()}))
    elif args.command == 'email-once':
        from .email_delivery import deliver_email
        print(json.dumps({'attempted': deliver_email()}))
    elif args.command == 'create-admin':
        password = getpass.getpass('Password (12+ characters): ')
        if len(password) < 12: parser.error('密码至少12位')
        if password != getpass.getpass('Confirm password: '): parser.error('密码不一致')
        with Session() as db:
            if db.scalar(select(User).where(User.username == args.username)): parser.error('用户已存在；不覆盖')
            db.add(User(username=args.username, password_hash=PasswordHasher().hash(password), role='admin')); db.commit()
        print('管理员已创建')
    elif args.command == 'crawl-once':
        if not 1 <= args.pages <= 10: parser.error('单次页数须为1–10，可用--backfill续扫')
        from .service import crawl, deliver_local
        print(json.dumps(crawl(args.source, args.pages, backfill=args.backfill), ensure_ascii=False)); deliver_local()
    elif args.command == 'refresh-details':
        if not 1 <= args.limit <= 5: parser.error('每次复查限1–5条')
        from .service import refresh_details, deliver_local
        print(json.dumps(refresh_details(args.source, args.limit), ensure_ascii=False)); deliver_local()
    elif args.command == 'remind-once':
        from .notifications import generate_deadline_reminders
        from .service import deliver_local
        print(json.dumps({'created': generate_deadline_reminders()})); deliver_local()
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
            result = ingest(db, args.source, args.url, Path(args.path).read_text(), observed_at=args.observed_at); db.commit()
        print(result); deliver_local()

if __name__ == '__main__': main()
