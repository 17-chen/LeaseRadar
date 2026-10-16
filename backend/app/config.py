import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'private')))
DATA.mkdir(parents=True, exist_ok=True)
# Optional private configuration, loaded before all service settings; env always wins.
runtime_file = DATA / 'runtime.json'
if runtime_file.exists():
    allowed = {'APP_MODE','COOKIE_SECURE','EMAIL_ENABLED','EMAIL_USER_ID','EMAIL_RECIPIENT','EMAIL_START_AT',
               'SOURCE_DOCUMENT_DOWNLOADS_ENABLED','SOURCE_DOCUMENTS_ENABLED','SOURCE_DOCUMENTS_USER_ID',
               'SOURCE_ALERT_EMAIL_ENABLED','SMTP_HOST','SMTP_PORT','SMTP_SECURITY','SMTP_FROM','SMTP_USERNAME','SMTP_PASSWORD'}
    if runtime_file.stat().st_size > 32000: raise ValueError('runtime.json exceeds size limit')
    configuration = json.loads(runtime_file.read_text())
    if not isinstance(configuration,dict) or set(configuration)-allowed: raise ValueError('runtime.json has unsupported keys')
    for key,value in configuration.items():
        if not isinstance(value,(str,int,bool)): raise ValueError('runtime.json values must be strings, numbers or booleans')
        os.environ.setdefault(key,str(value).lower() if isinstance(value,bool) else str(value))
    del configuration
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATA / "leaseradar.db"}')
MODE = os.getenv('APP_MODE', 'live')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
ALLOWED_HOSTS = {'www.nongjy.cn', 'www.wzpt.edu.cn', 'www.wzcqpt.com'}
