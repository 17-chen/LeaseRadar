import csv
import io

from app.db import Session
from app.listing_views import in_quick_view
from app.service import ingest
from test_core import sample, client_for


def test_personal_views_keep_closed_favorites_and_only_active_followups():
    row = {'status': 'closed', 'registration_deadline': '2020-01-01T00:00:00+00:00',
           'personal_followups': [{'favorite': True, 'status': '待联系'}]}
    assert in_quick_view(row, 'favorites') and in_quick_view(row, 'following')
    for status in ('未查看', '已查看', '放弃', '已成交'):
        changed = {**row, 'personal_followups': [{'favorite': True, 'status': status}]}
        assert in_quick_view(changed, 'favorites')
        assert not in_quick_view(changed, 'following')
    assert not in_quick_view({}, 'favorites')
    assert not in_quick_view({}, 'following')


def test_personal_views_are_private_filterable_exportable_and_removable():
    with Session() as db:
        lid, _ = ingest(db, 'nongjy', 'https://www.nongjy.cn/web/propertyBid/detail/881', sample())
        db.commit()
    member, other = client_for('member'), client_for('other')
    assert member.patch(f'/api/v1/listings/{lid}/followup', json={
        'status': '待联系', 'favorite': True, 'note': 'PRIVATE_PERSONAL_SENTINEL'}).status_code == 200
    for view in ('favorites', 'following'):
        result = member.post('/api/v1/listings/search', json={'view': view}).json()
        assert result['total'] == 1 and result['items'][0]['id'] == lid
        assert other.post('/api/v1/listings/search', json={'view': view}).json()['total'] == 0
        response = member.post('/api/v1/exports/listings.csv', json={'view': view})
        rows = list(csv.DictReader(io.StringIO(response.text.lstrip('\ufeff'))))
        assert len(rows) == 1 and rows[0]['id'] == str(lid)
        assert 'PRIVATE_PERSONAL_SENTINEL' not in response.text
        assert member.post('/api/v1/listings/search', json={'view': view, 'filters': {'area_m2_min':'999'}}).json()['total'] == 0
    assert member.patch(f'/api/v1/listings/{lid}/followup', json={
        'status':'已成交', 'favorite':False, 'note':''}).status_code == 200
    for view in ('favorites', 'following'):
        assert member.post('/api/v1/listings/search', json={'view':view}).json()['total'] == 0


def test_noncanonical_followup_survives_grouping_without_exposing_notes():
    with Session() as db:
        left, _ = ingest(db, 'nongjy', 'https://www.nongjy.cn/web/propertyBid/detail/882', sample())
        right, _ = ingest(db, 'nongjy', 'https://www.nongjy.cn/web/propertyBid/detail/883', sample())
        db.commit()
    member, other, admin = client_for('member'), client_for('other'), client_for('admin')
    assert member.patch(f'/api/v1/listings/{right}/followup', json={
        'status':'预约看铺', 'favorite':True, 'note':'PRIVATE_SECONDARY_NOTE'}).status_code == 200
    response = admin.post('/api/v1/listing-relations', json={
        'left_id':left, 'right_id':right, 'kind':'same_round', 'reason':'合成样本确认同批挂牌关系'})
    assert response.status_code == 200, response.text
    for view in ('favorites', 'following'):
        result = member.post('/api/v1/listings/search', json={'view':view}).json()
        assert result['total'] == 1
        row = result['items'][0]
        assert row['id'] == left
        assert row['personal_followups'] == [{'listing_id':right, 'status':'预约看铺', 'favorite':True}]
        assert 'PRIVATE_SECONDARY_NOTE' not in str(row['personal_followups'])
        assert other.post('/api/v1/listings/search', json={'view':view}).json()['total'] == 0
