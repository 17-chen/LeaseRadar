import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'private')))
DATA.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATA / "leaseradar.db"}')
MODE = os.getenv('APP_MODE', 'live')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
ALLOWED_HOSTS = {'www.nongjy.cn', 'www.wzpt.edu.cn', 'www.wzcqpt.com'}
