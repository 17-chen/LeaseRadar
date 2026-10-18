"""Conservative labeled-table adapter for university notices."""
import re
from datetime import datetime
from decimal import Decimal
from urllib.parse import urljoin,urlsplit
from zoneinfo import ZoneInfo

NUMBER=r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'


def date_value(value,with_time=False):
    pattern=r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?'
    if with_time:pattern+=r'\s*(\d{1,2})[时:：](\d{1,2})(?:分|:00)?'
    match=re.fullmatch(pattern,value.strip())
    if not match:return None
    try:
        parts=list(map(int,match.groups()));dt=datetime(*parts,tzinfo=ZoneInfo('Asia/Shanghai'))
        return dt.isoformat() if with_time else dt.date().isoformat()
    except ValueError:return None


def parse(html,url):
    from ..collectors import soup_text,location_parts,SourceError
    soup,text=soup_text(html);article=soup.select_one('.wp_articlecontent')
    if article is None:raise SourceError('高校公告正文选择器失效')
    title=soup.select_one('h1.arti_title, .Article_Title, h1') or soup.title
    if title is None or not title.get_text(strip=True):raise SourceError('高校公告标题缺失')
    title=title.get_text(' ',strip=True)
    fields={'title':title,'source_url':url,'status':'unknown','price_kind':None,'period_basis':None,
            'property_type':None,'environment':None,'operation':None,'parser_version':'wzpt-table-v4',
            'warnings':['发布单位不代表标的位于校园，所在环境待核实','用途原文不等于已取得经营许可；经营用途保持待确认']}
    evidence={'title':title};candidates={};uses=[]
    def collect(key,value,quote):candidates.setdefault(key,[]).append((value,quote))
    for row in article.select('tr'):
        cells=[c.get_text(' ',strip=True) for c in row.find_all(['td','th'],recursive=False)]
        for i,label in enumerate(cells[:-1]):
            label=label.rstrip('：:').strip();value=cells[i+1];quote=label+'：'+value
            if label in ('挂牌价格','租金挂牌价'):
                m=re.fullmatch('('+NUMBER+r')\s*(万元|元)\s*/\s*(年|月)',value)
                amount=format((Decimal(m[1].replace(',',''))*(10000 if m[2]=='万元' else 1)).normalize(),'f') if m else None
                collect('raw_amount',amount,quote);collect('period_basis',('first_year' if m[3]=='年' else 'monthly') if m else None,quote)
                collect('price_kind','asking' if m else None,quote)
            elif label=='出租面积':
                m=re.fullmatch(r'(?:面积)?\s*(?:约)?\s*('+NUMBER+r')\s*(?:平方米|㎡)(?:[，,]\s*最终以实测面积为准[。.])?[。.]?',value)
                collect('area_m2',format(Decimal(m[1].replace(',','')).normalize(),'f') if m else None,quote)
                if '约' in value:fields['warnings'].append('面积为公告约数，最终实测面积待核验')
            elif label=='出租标的地址':collect('address',value or None,quote)
            elif label=='所在地区':
                city,district=location_parts(value)
                collect('city',city,quote);collect('district',district,quote)
            elif label=='信息披露截止日期':collect('disclosure_deadline',date_value(value),quote)
            elif label=='报名截止时间':collect('registration_deadline',date_value(value,True),quote)
            elif label=='竞价截止时间':collect('auction_deadline',date_value(value,True),quote)
            elif label=='出租用途':uses.append(quote)
            elif label in ('租期','有无免租期','租金挂牌价备注'):
                collect({'租期':'lease_term_text','有无免租期':'free_rent_text','租金挂牌价备注':'rent_notes'}[label],value or None,quote)
    for key,values in candidates.items():
        distinct={v for v,q in values};evidence[key]='；'.join(dict.fromkeys(q for v,q in values))[:4000]
        if len(distinct)==1 and None not in distinct:fields[key]=next(iter(distinct))
        else:
            fields[key]=None;fields['warnings'].append(f'{key}有冲突或格式未核实，保留未知')
    # Price and basis are one assertion; never combine an amount from one row
    # with a different row's period when either assertion is unresolved.
    if fields.get('raw_amount') is None or fields.get('period_basis') is None:
        fields['raw_amount']=None;fields['period_basis']=None;fields['price_kind']=None
    if uses:
        fields['disclosed_use']='；'.join(dict.fromkeys(uses))[:10000];evidence['disclosed_use']=fields['disclosed_use']
    fields['attachments']=[]
    for link in article.select('a[href]'):
        target=urljoin(url,link['href'])
        try:
            p=urlsplit(target)
            safe=p.scheme=='https' and p.hostname in ('www.nongjy.cn','www.wzpt.edu.cn','www.wzcqpt.com') and not p.username and not p.password and p.port in (None,443)
        except ValueError:safe=False
        if safe and re.search(r'\.(pdf|docx)(?:\?|$)',target,re.I) and not any(a['url']==target for a in fields['attachments']):
            fields['attachments'].append({'name':link.get_text(' ',strip=True),'url':target})
    if not candidates:fields['warnings'].append('链接型公告：正文未提供结构化字段，需核验所链接交易平台')
    if 'disclosure_deadline' in fields and not fields.get('registration_deadline'):
        fields['warnings'].append('信息披露截止不替代报名截止，报名时限仍待核验')
    return fields,evidence,article.get_text(' ',strip=True)
