from pathlib import Path
from datetime import datetime,timezone
import pytest
from app.collectors import wzpt_parse,SourceError
from app.domain import normalize_price,match

URL='https://www.wzpt.edu.cn/2025/0710/c739771a2844693/page.htm'
FIXTURE=Path(__file__).resolve().parents[2]/'fixtures/wzpt/labeled_notice.html'

def table(rows):return '<title>合成公告</title><div class="wp_articlecontent"><table>'+''.join('<tr><td>'+k+'</td><td>'+v+'</td></tr>' for k,v in rows)+'</table></div>'

def test_fixture_evidence_and_no_permission_inference():
    fields,evidence,text=wzpt_parse(FIXTURE.read_text(),URL)
    assert fields['raw_amount']=='234000' and fields['period_basis']=='first_year' and fields['area_m2']=='1500'
    assert normalize_price(fields)['first_year_monthly']=='19500.00'
    assert fields['operation'] is None and fields['environment'] is None
    assert '审批' in fields['disclosed_use'] and fields['free_rent_text']=='无'
    assert not fields.get('registration_deadline')
    assert all(key in evidence for key in ['raw_amount','period_basis','area_m2','disclosed_use','lease_term_text'])
    assert match(fields,{'registration_open':True},datetime(2026,10,18,tzinfo=timezone.utc))['verdict']=='fail'


@pytest.mark.parametrize('rows',[
 [('挂牌价格','10000 元/月'),('租金挂牌价','20000 元/月')],
 [('挂牌价格','10000 元/月'),('租金挂牌价','10000 元/年')],
 [('挂牌价格','10000 元/月'),('租金挂牌价','面议')],
 [('挂牌价格','10000元，周期未知')],
])
def test_price_conflicts_and_unknown_never_normalize(rows):
    fields,evidence,text=wzpt_parse(table(rows),URL)
    assert fields['raw_amount'] is None and fields['period_basis'] is None
    assert normalize_price(fields)['first_year_monthly'] is None
    assert evidence['raw_amount']


@pytest.mark.parametrize('value',['100至200平方米','100平方米和200平方米','1,2平方米','待测量'])
def test_ambiguous_area_is_not_first_number(value):
    fields,evidence,text=wzpt_parse(table([('出租面积',value)]),URL)
    assert fields.get('area_m2') is None and value in evidence['area_m2']


def test_only_explicit_registration_datetime_becomes_deadline():
    fields,evidence,text=wzpt_parse(table([('信息披露截止日期','2099-07-23'),('报名截止时间','2099年7月22日16时30分'),('竞价截止时间','2099-07-24 10:00')]),URL)
    assert fields['registration_deadline']=='2099-07-22T16:30:00+08:00'
    assert fields['auction_deadline']=='2099-07-24T10:00:00+08:00'
    assert fields['disclosure_deadline']=='2099-07-23'


@pytest.mark.parametrize('value',['2099-07-23','2099-02-30 10:00','另行通知'])
def test_unknown_registration_time_not_end_of_day(value):
    fields,evidence,text=wzpt_parse(table([('报名截止时间',value)]),URL)
    assert fields.get('registration_deadline') is None


def test_conflicting_address_and_deadline_remain_unknown():
    fields,evidence,text=wzpt_parse(table([('出租标的地址','合成甲'),('出租标的地址','合成乙'),('报名截止时间','2099-07-22 16:30'),('报名截止时间','2099-07-23 16:30')]),URL)
    assert fields['address'] is None and fields['registration_deadline'] is None


def test_attachment_metadata_is_article_scoped_and_whitelisted():
    html=table([]).replace('</div>','<a href="/test.docx">合成附件</a><a href="https://127.0.0.1/x.pdf">坏链接</a><a href="https://other.example/x.pdf">外部链接</a></div>')+'<a href="/outside.pdf">页脚</a>'
    fields,_,_=wzpt_parse(html,URL)
    assert fields['attachments']==[{'name':'合成附件','url':'https://www.wzpt.edu.cn/test.docx'}]


def test_empty_selector_or_missing_title_is_failure():
    with pytest.raises(SourceError):wzpt_parse('<title>x</title>',URL)
    with pytest.raises(SourceError):wzpt_parse('<div class="wp_articlecontent">text</div>',URL)


def test_ingest_historical_fixture_has_evidence_and_keeps_observation_time():
    from app.db import Session,Version,Evidence,SourceRecord
    from app.service import ingest,listing_data
    from sqlalchemy import select,func
    at='2025-07-10T10:00:00+08:00'
    with Session() as db:
        for _ in range(2):identity,_=ingest(db,'wzpt',URL,FIXTURE.read_text(),observed_at=at);db.commit()
        assert db.scalar(select(func.count()).select_from(Version))==1
        version=db.scalar(select(Version));assert version.fields['first_year_monthly']=='19500.00'
        assert '审批' in db.scalar(select(Evidence).where(Evidence.field=='disclosed_use')).quote
        record=db.scalar(select(SourceRecord));assert datetime.fromisoformat(record.last_checked_at)==datetime.fromisoformat(at)


def test_adapter_upgrade_is_reprocessing_not_market_change(monkeypatch):
    from app.db import Session,Event
    from app.service import ingest
    import app.service as service
    from sqlalchemy import select
    original=service.PARSERS['wzpt']
    def legacy(html,url):
        fields,evidence,text=original(html,url);fields['parser_version']='wzpt-html-v3'
        return fields,evidence,text
    with Session() as db:
        monkeypatch.setitem(service.PARSERS,'wzpt',legacy)
        ingest(db,'wzpt',URL,FIXTURE.read_text());db.commit()
        monkeypatch.setitem(service.PARSERS,'wzpt',original)
        ingest(db,'wzpt',URL,FIXTURE.read_text());db.commit()
        assert [e.kind for e in db.scalars(select(Event).order_by(Event.id))]==['new','reprocessing']
