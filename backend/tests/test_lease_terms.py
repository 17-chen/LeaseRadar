from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.lease_terms import LeasePlan,calculate
from test_core import client_for

E={key:'合成合同依据：该项条款明确' for key in ['basis','term_months','amount','escalation','free_months','fees','deposit','proration','fixed_rent','amount_before_free']}

def test_annual_compound_rent_not_deposit_cost():
    r=calculate(LeasePlan(basis='first_year',amount='120000',term_months=36,annual_escalation_percent='5',annual_compound=True,refundable_deposit='20000',evidence=E))
    assert r['total_rent']=='378300.00' and r['average_monthly']=='10508.33'
    assert r['first_year_monthly']=='10000.00' and r['refundable_deposit']=='20000.00'
    assert r['nonrefundable_fees'] is None and r['cost_complete'] is False


def test_total_term_never_invents_first_year_or_schedule():
    r=calculate(LeasePlan(basis='total_term',amount='120000',term_months=60,evidence=E))
    assert r['average_monthly']=='2000.00' and r['first_year_monthly'] is None and r['schedule']==[]


def test_free_months_and_zero_are_explicit():
    r=calculate(LeasePlan(basis='monthly',amount='10000',term_months=12,free_months=[1,2],amount_before_free=True,nonrefundable_fees='0',evidence=E))
    assert r['total_rent']=='100000.00' and r['first_year_monthly']=='8333.33' and r['nonrefundable_fees']=='0.00'
    assert r['schedule'][0]['rent']=='0.00'


def test_partial_year_requires_explicit_rule():
    p=LeasePlan(basis='first_year',amount='120000',term_months=15,fixed_rent=True,evidence=E)
    assert calculate(p)['total_rent'] is None
    assert calculate(p.model_copy(update={'prorate_partial_year':True}))['total_rent']=='150000.00'


def test_segments_exact_coverage_and_evidence():
    p=LeasePlan(basis='segments',term_months=15,segments=[{'start_month':1,'end_month':3,'monthly':'0','quote':'合同明确前三月免租'}, {'start_month':4,'end_month':15,'monthly':'10000','quote':'第四至十五个月月租一万元'}],evidence=E)
    r=calculate(p);assert r['total_rent']=='120000.00' and r['average_monthly']=='8000.00' and r['segment_evidence']
    with pytest.raises(ValidationError):LeasePlan(basis='segments',term_months=15,segments=[{'start_month':2,'end_month':15,'monthly':'10000','quote':'合同明确逐月金额'}],evidence=E)

@pytest.mark.parametrize('updates',[{'evidence':{}},{'amount':'NaN'},{'free_months':[1,1]},{'annual_escalation_percent':'5'},{'term_months':0}])
def test_invalid_or_unsupported_terms_rejected(updates):
    with pytest.raises(ValidationError):LeasePlan(**{'basis':'monthly','amount':'10000','term_months':12,'evidence':E,**updates})


def test_authenticated_api_never_writes_financial_records():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import Session,Version
    from sqlalchemy import select,func
    assert TestClient(app).post('/api/v1/lease-calculations',json={}).status_code==401
    c=client_for('member')
    r=c.post('/api/v1/lease-calculations',json={'basis':'monthly','amount':'0','term_months':12,'evidence':E})
    assert r.status_code==200 and r.json()['total_rent']=='0.00'
    with Session() as db:assert db.scalar(select(func.count()).select_from(Version))==0


def test_unknown_future_rent_never_assumes_zero_escalation():
    r=calculate(LeasePlan(basis='first_year',amount='120000',term_months=36,evidence=E))
    assert r['total_rent'] is None
    with pytest.raises(ValidationError):LeasePlan(basis='monthly',amount='10000',term_months=12,free_months=[1],evidence=E)
