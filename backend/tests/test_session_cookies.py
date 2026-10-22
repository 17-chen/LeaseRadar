"""One browser cookie jar, three databases, different ports on the same host."""
import os
import subprocess
import sys

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main
from app.db import Base, User
from app.session_cookies import session_cookie_name


@pytest.mark.parametrize('mode', ['live', 'replay'])
def test_existing_non_demo_cookie_is_compatible(mode):
    assert session_cookie_name(mode, 'sqlite:///one.db') == 'lease_session'
    assert session_cookie_name(mode, 'sqlite:///two.db') == 'lease_session'


def test_demo_identity_is_stable_private_and_different_per_database():
    identity = 'postgresql://private-user:private-password@localhost/private-db'
    name = session_cookie_name('demo', identity)
    assert name == session_cookie_name('demo', identity)
    assert name.startswith('lease_demo_') and name.isascii()
    assert 'private' not in name and ':' not in name and '/' not in name
    assert name != session_cookie_name('demo', identity + '-other')
    assert name != session_cookie_name('live', identity)


def test_startup_uses_demo_namespace(tmp_path):
    env = {**os.environ, 'DATA_DIR': str(tmp_path), 'APP_MODE': 'demo',
           'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'isolated.db')}
    result = subprocess.run([sys.executable, '-c', '''
from app.config import SESSION_COOKIE_NAME, MODE, DATABASE_URL
from app.main import SESSION_COOKIE_NAME as api_cookie
from app.session_cookies import session_cookie_name
assert api_cookie == SESSION_COOKIE_NAME == session_cookie_name(MODE, DATABASE_URL)
assert api_cookie != 'lease_session'
'''], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('secure', [False, True])
def test_shared_host_login_csrf_and_logout_are_isolated(tmp_path, monkeypatch, secure):
    engines = []
    instances = []
    for index, mode in enumerate(('live', 'demo', 'demo')):
        url = 'sqlite:///' + str(tmp_path / f'instance-{index}.db')
        engine = create_engine(url, connect_args={'check_same_thread': False})
        engines.append(engine)
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        with factory() as db:
            db.add(User(username=f'user-{index}', role='member',
                        password_hash=main.hasher.hash('synthetic-test-password')))
            db.commit()
        instances.append((factory, session_cookie_name(mode, url)))

    # Cookies are scoped to host/path, so ports 8100..8102 share this browser jar.
    jar = httpx.Cookies()
    csrf = {}

    def request(index, method, path, **kwargs):
        nonlocal jar
        factory, name = instances[index]
        monkeypatch.setattr(main, 'Session', factory)
        monkeypatch.setattr(main, 'SESSION_COOKIE_NAME', name)
        monkeypatch.setattr(main, 'COOKIE_SECURE', secure)
        with TestClient(main.app, base_url=f'https://localhost:{8100 + index}', cookies=jar) as client:
            response = client.request(method, path, **kwargs)
            jar = client.cookies
        return response

    try:
        for index in range(3):
            response = request(index, 'POST', '/api/v1/auth/login', json={
                'username': f'user-{index}', 'password': 'synthetic-test-password'})
            assert response.status_code == 200
            csrf[index] = response.json()['csrf']
            cookie = response.headers['set-cookie']
            assert cookie.startswith(instances[index][1] + '=')
            assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Path=/' in cookie
            assert ('; Secure' in cookie) is secure
        assert len(list(jar.jar)) == 3
        for index in range(3):
            response = request(index, 'GET', '/api/v1/auth/me')
            assert response.status_code == 200 and response.json()['username'] == f'user-{index}'
        assert request(1, 'POST', '/api/v1/auth/logout').status_code == 403
        assert request(1, 'POST', '/api/v1/auth/logout', headers={'X-CSRF-Token': csrf[0]}).status_code == 403
        old_demo_token = jar.get(instances[1][1])
        response = request(1, 'POST', '/api/v1/auth/logout', headers={'X-CSRF-Token': csrf[1]})
        assert response.status_code == 200
        assert response.headers['set-cookie'].startswith(instances[1][1] + '=')
        assert 'Max-Age=0' in response.headers['set-cookie']
        assert len(list(jar.jar)) == 2
        assert request(1, 'GET', '/api/v1/auth/me').status_code == 401
        with TestClient(main.app, base_url='https://localhost:8101',
                        cookies={instances[1][1]: old_demo_token}) as client:
            assert client.get('/api/v1/auth/me').status_code == 401
        for index in (0, 2):
            assert request(index, 'GET', '/api/v1/auth/me').json()['username'] == f'user-{index}'
        # Even a valid legacy token must never be read as a DEMO fallback.
        monkeypatch.setattr(main, 'Session', instances[0][0])
        monkeypatch.setattr(main, 'SESSION_COOKIE_NAME', instances[1][1])
        with TestClient(main.app, base_url='https://localhost:8101', cookies=jar) as client:
            assert client.get('/api/v1/auth/me').status_code == 401
    finally:
        for engine in engines:
            engine.dispose()
