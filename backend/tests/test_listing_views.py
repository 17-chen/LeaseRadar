from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.listing_views import in_quick_view
from app.main import app


AT = datetime(2026, 10, 18, 8, 0, tzinfo=timezone.utc)


def test_deadline_view_uses_registration_cutoff_and_excludes_closed_rounds():
    row = {'status': 'unknown',
           'registration_deadline': '2026-10-20T16:00:00+08:00',
           'auction_deadline': '2026-11-01T10:00:00+08:00'}
    assert in_quick_view(row, 'deadline', AT)
    assert not in_quick_view({**row, 'status': 'closed'}, 'deadline', AT)
    assert not in_quick_view({**row, 'registration_deadline': '2026-10-17T16:00:00+08:00'}, 'deadline', AT)
    assert not in_quick_view({**row, 'registration_deadline': None}, 'deadline', AT)


def test_recent_view_uses_first_record_creation_not_last_recheck():
    row = {'created_at': '2026-10-01T00:00:00+00:00',
           'last_checked_at': '2026-10-18T07:00:00+00:00'}
    assert not in_quick_view(row, 'recent', AT)
    assert in_quick_view({**row, 'created_at': '2026-10-17T07:00:00+00:00'}, 'recent', AT)


def test_review_view_preserves_price_and_source_uncertainty():
    reliable = {'status': 'open', 'area_m2': '60', 'raw_amount': '90000',
                'period_basis': 'first_year', 'registration_deadline': '2026-10-25T12:00:00+08:00',
                'match': {'verdict': 'pass'}}
    assert not in_quick_view(reliable, 'review', AT)
    assert in_quick_view({**reliable, 'period_basis': None}, 'review', AT)
    assert in_quick_view({**reliable, 'source_conflicts': ['raw_amount']}, 'review', AT)
    assert in_quick_view({**reliable, 'match': {'verdict': 'unknown'}}, 'review', AT)
    assert not in_quick_view({**reliable, 'status': 'closed', 'period_basis': None}, 'review', AT)
    assert not in_quick_view({**reliable, 'registration_deadline': '2026-10-17T12:00:00+08:00', 'period_basis': None}, 'review', AT)


def test_quick_view_filters_before_pagination(monkeypatch):
    from app import resolution
    recent = datetime.now(timezone.utc).isoformat()
    later = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    rows = [{'id': i, 'created_at': recent, 'status': 'open',
             'registration_deadline': later, 'period_basis': 'monthly',
             'raw_amount': '1000', 'area_m2': '50'} for i in range(25)]
    rows[-1]['status'] = 'unknown'
    monkeypatch.setattr(resolution, 'grouped_rows', lambda db, user_id: rows)
    client = TestClient(app)
    login = client.post('/api/v1/auth/login', json={'username': 'member', 'password': 'test-password-123'})
    assert login.status_code == 200
    client.headers['X-CSRF-Token'] = login.json()['csrf']
    response = client.post('/api/v1/listings/search', json={'view': 'review', 'page': 1, 'limit': 1})
    assert response.status_code == 200
    assert response.json()['total'] == 1 and response.json()['items'][0]['id'] == 24
    response = client.post('/api/v1/listings/search', json={'view': 'recent', 'page': 2, 'limit': 24})
    assert response.status_code == 200
    assert response.json()['total'] == 25 and len(response.json()['items']) == 1


def test_filtered_export_uses_all_matching_pages_and_csv_protection(monkeypatch):
    import csv, io
    from app import resolution
    recent = datetime.now(timezone.utc).isoformat()
    rows = [{'id': i, 'title': '=HYPERLINK("synthetic")', 'created_at': recent,
             'area_m2': '50', 'raw_amount': None, 'period_basis': None,
             'status': 'unknown'} for i in range(30)]
    rows.append({'id': 99, 'title': 'excluded', 'created_at': recent, 'area_m2': '10'})
    monkeypatch.setattr(resolution, 'grouped_rows', lambda db, user_id: rows)
    client = TestClient(app)
    assert client.post('/api/v1/exports/listings.csv', json={}).status_code == 401
    login = client.post('/api/v1/auth/login', json={'username': 'member', 'password': 'test-password-123'})
    assert client.post('/api/v1/exports/listings.csv', json={}).status_code == 403
    client.headers['X-CSRF-Token'] = login.json()['csrf']
    query = {'view': 'review', 'filters': {'area_m2_min': '30', 'first_year_monthly_max': '12000'}, 'page': 2, 'limit': 1}
    result = client.post('/api/v1/exports/listings.csv', json=query)
    assert result.status_code == 200
    values = list(csv.DictReader(io.StringIO(result.text.lstrip('\ufeff'))))
    assert len(values) == 30
    assert all(r['raw_amount'] == '' and r['title'].startswith("'=") for r in values)
    assert client.post('/api/v1/exports/listings.csv', json={**query, 'include_unknown': False}).text.count('\n') == 1
    assert client.post('/api/v1/exports/listings.csv', json={'view': 'invalid'}).status_code == 422


def test_quick_view_time_boundaries_and_ambiguous_dates():
    assert in_quick_view({'created_at': (AT-timedelta(days=7)).isoformat()}, 'recent', AT)
    assert not in_quick_view({'created_at': (AT+timedelta(seconds=1)).isoformat()}, 'recent', AT)
    assert not in_quick_view({'registration_deadline': AT.isoformat()}, 'deadline', AT)
    assert in_quick_view({'registration_deadline': (AT+timedelta(days=7)).isoformat()}, 'deadline', AT)
    assert not in_quick_view({'registration_deadline': '2026-10-20'}, 'deadline', AT)
    assert not in_quick_view({'registration_deadline': '2026-10-20T16:00:00'}, 'deadline', AT)
