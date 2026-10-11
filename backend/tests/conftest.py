import os
import tempfile
os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='leaseradar-tests-')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.environ['DATA_DIR'] + '/test.db'
os.environ['APP_MODE'] = 'demo'
import pytest
from app.db import Base, engine, Session, User, seed_sources
from argon2 import PasswordHasher

@pytest.fixture(autouse=True)
def clean_db(monkeypatch):
    # Tests never inherit a real recipient or SMTP credential from the host.
    monkeypatch.setenv('EMAIL_ENABLED', 'false')
    monkeypatch.setenv('SMTP_USERNAME', '')
    monkeypatch.setenv('SMTP_PASSWORD', '')
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with Session() as db:
        seed_sources(db)
        for name, role in [('admin', 'admin'), ('member', 'member'), ('other', 'member')]:
            db.add(User(username=name, role=role, password_hash=PasswordHasher().hash('test-password-123')))
        db.commit()
    yield
