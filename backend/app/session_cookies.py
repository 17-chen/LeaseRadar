"""Cookie namespaces for isolated local demos; ports do not isolate cookies."""
import hashlib


def session_cookie_name(mode: str, database_url: str) -> str:
    # Keep existing LIVE/replay sessions compatible. Never expose DB paths/credentials.
    # This prevents accidental overwrites, not access by untrusted same-host apps.
    if mode != 'demo':
        return 'lease_session'
    identity = hashlib.sha256(database_url.encode()).hexdigest()[:24]
    return f'lease_demo_{identity}'
