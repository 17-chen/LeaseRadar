"""Verified HTML contracts; unknown values are deliberately preserved."""
import hashlib
import ipaddress
import re
import socket
import time
from datetime import datetime
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
import httpx
from bs4 import BeautifulSoup
from .config import ALLOWED_HOSTS

class SourceError(RuntimeError):
    pass

def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise SourceError('URL不在已核准HTTPS来源范围')
    for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise SourceError('拒绝非公网地址')
    return url

def fetch(url):
    # No redirects: new destinations must be explicitly reviewed.
    validate_url(url)
    with httpx.Client(timeout=25, follow_redirects=False, trust_env=False,
                      headers={'User-Agent': 'LeaseRadar/0.1 (public source research)'}) as client:
        with client.stream('GET', url) as response:
            if response.status_code != 200:
                raise SourceError(f'HTTP {response.status_code}; 重定向/403不自动绕过')
            if 'text/html' not in response.headers.get('content-type', ''):
                raise SourceError('非HTML响应')
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise SourceError('页面超过2MB限制')
            return bytes(body).decode('utf-8', errors='replace')

def soup_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    return soup, soup.get_text(' ', strip=True)

def iso_date(value):
    return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo('Asia/Shanghai')).isoformat()

def nongjy_discover(html, page=1):
    soup = BeautifulSoup(html, 'html.parser')
    paths = list(dict.fromkeys(a['href'] for a in soup.select('a[href]') if re.fullmatch(r'/web/propertyBid/detail/\d+', a['href'])))
    if not paths:
        raise SourceError('列表无有效详情链接，不能当作正常空结果')
    text = soup.get_text(' ', strip=True)
    total = re.search(r'/\s*(\d+)\s*页', text)
    if not total:
        raise SourceError('未识别分页总数')
    return ['https://www.nongjy.cn' + p for p in paths], int(total.group(1))

def nongjy_parse(html, url):
    soup, text = soup_text(html)
    title_node = soup.select_one('.cont-info-left-title')
    if not title_node:
        raise SourceError('详情标题选择器失效')
    fields = {'title': title_node.get_text(' ', strip=True), 'source_url': url,
              'property_type': None, 'environment': None, 'operation': None,
              'period_basis': None, 'price_kind': 'starting_bid', 'status': 'unknown',
              'parser_version': 'nongjy-html-v2', 'warnings': []}
    evidence = {'title': fields['title']}
    for label, key in [('项目位置：', 'address'), ('项目编号：', 'project_code'), ('交易单位：', 'area_m2'), ('保证金：', 'deposit')]:
        node = next((n for n in soup.select('.cont-info-left-bt') if n.get_text(strip=True) == label), None)
        if node:
            value = node.parent.get_text(' ', strip=True).replace(label, '', 1).strip()
            evidence[key] = label + value
            if key in ('area_m2', 'deposit'):
                found = re.search(r'(\d+(?:\.\d+)?)', value)
                fields[key] = found.group(1) if found and (key != 'area_m2' or '㎡' in value) else None
                if key == 'area_m2': fields['area_approx'] = '约' in value
            else:
                fields[key] = value
    amount = soup.select_one('.cont-info-left-timebox-price')
    if amount:
        value = amount.get_text(strip=True)
        if re.fullmatch(r'\d+(?:\.\d+)?', value):
            fields['raw_amount'] = value
            evidence['raw_amount'] = amount.parent.get_text(' ', strip=True)
            label = evidence['raw_amount']
            fields['price_kind'] = 'sale' if '成交价' in label else 'asking' if '挂牌价' in label else 'starting_bid' if '起始价' in label else None
    for label, key in [('报名截止时间', 'registration_deadline'), ('竞价截止时间', 'auction_deadline')]:
        found = re.search(label + r'：\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text)
        if found:
            fields[key] = iso_date(found.group(1))
            evidence[key] = found.group(0)
    # Business state only from visible summary, never from instructions/body hypotheticals.
    summary = soup.select_one('.cont-info-left-title').parent.get_text(' ', strip=True)
    for marker, state in [('已流标', 'failed'), ('已成交', 'sold'), ('已撤回', 'withdrawn'), ('报名已截止', 'closed')]:
        if marker in summary:
            fields['status'] = state
            evidence['status'] = marker
            break
    if fields['status'] == 'unknown' and soup.select_one('.signupButton'):
        fields['status'] = 'open'
        evidence['status'] = soup.select_one('.signupButton').get_text(' ', strip=True)
    address = fields.get('address', '')
    city = re.search(r'([\u4e00-\u9fff]{2,8}市)', address)
    district = re.search(r'市([^市]{2,6}[区县])', address)
    fields['city'] = city.group(1) if city else None
    fields['district'] = district.group(1) if district else None
    for word, kind in [('商铺', 'shop'), ('店面', 'shop'), ('厂房', 'warehouse'), ('仓库', 'warehouse')]:
        if word in fields['title']:
            fields['property_type'] = kind
            evidence['property_type'] = fields['title']
            break
    fields['attachments'] = [{'name': a.get_text(' ', strip=True), 'url': urljoin(url, a['href'])}
                              for a in soup.select('a[href]') if re.search(r'\.(docx?|pdf|xlsx?)(?:\?|$)', a['href'], re.I)]
    fields['warnings'] = ['价格周期尚未由对应标的表格或合同核实；不换算月租', '经营用途未核实']
    fields['bundle'] = bool(re.search(r'[二三四五六七八九十两\d]+间|\d+幢.*\d+幢', fields['title']))
    if fields['bundle']: fields['warnings'].append('整体出租，面积和价格按整体保留，不拆分到成员')
    if fields['attachments'] or soup.select('img[src]'):
        fields['warnings'].append('附件/图片中的条款尚未解析')
    return fields, evidence, text

def wzpt_discover(html, page=1):
    soup = BeautifulSoup(html, 'html.parser')
    article_links = [a for a in soup.select('a[href]') if re.search(r'/page.htm$', a['href'])]
    if len(article_links) < 5:
        raise SourceError('高校栏目正常文章列表未识别')
    refs = [urljoin('https://www.wzpt.edu.cn', a['href']) for a in soup.select('a[href]')
            if re.search(r'租赁|招租|出租', a.get_text()) and re.search(r'/page.htm$', a['href'])]
    total = re.search(r'页码\s*\d+\s*/\s*(\d+)', soup.get_text(' ', strip=True))
    if not total: raise SourceError('高校栏目分页未识别')
    return list(dict.fromkeys(refs)), int(total.group(1))

def wzpt_parse(html, url):
    soup, text = soup_text(html)
    article = soup.select_one('.wp_articlecontent')
    if not article:
        raise SourceError('高校公告正文选择器失效')
    title = soup.title.get_text(strip=True)
    fields = {'title': title, 'source_url': url, 'status': 'unknown', 'price_kind': 'asking',
              'period_basis': None, 'property_type': None, 'environment': 'campus', 'operation': None,
              'parser_version': 'wzpt-html-v2', 'warnings': ['经营许可与披露截止是否为报名截止待核对']}
    evidence = {'title': title, 'environment': title}
    if not article.select('tr'):
        fields['warnings'].append('链接型公告：正文未提供结构化字段，需核验所链接交易平台')
    # Restrict extraction to known labeled table rows.
    for row in article.select('tr'):
        cells = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'], recursive=False)]
        for i, label in enumerate(cells[:-1]):
            value = cells[i+1]
            if label == '挂牌价格':
                m = re.search(r'([\d.]+)\s*(万元|元)\s*/\s*(年|月)', value)
                if m:
                    from decimal import Decimal
                    fields['raw_amount'] = str(Decimal(m.group(1)) * (10000 if m.group(2) == '万元' else 1))
                    # 年租金可以作一年口径，仅作为当前公布年租基准。
                    fields['period_basis'] = 'first_year' if m.group(3) == '年' else 'monthly'
                    evidence['raw_amount'] = evidence['period_basis'] = label + ' ' + value
            elif label == '出租面积':
                m = re.search(r'([\d.]+)\s*平方米', value)
                if m: fields['area_m2'] = m.group(1); evidence['area_m2'] = value
            elif label == '出租标的地址':
                fields['address'] = value; evidence['address'] = value
            elif label == '所在地区':
                city = re.search(r'(\S+市)', value)
                district = re.search(r'(\S+[区县])', value)
                fields['city'] = city.group(1) if city else None
                fields['district'] = district.group(1) if district else None
            elif label == '信息披露截止日期':
                fields['disclosure_deadline'] = value
                evidence['disclosure_deadline'] = value
    return fields, evidence, article.get_text(' ', strip=True)

PARSERS = {'nongjy': nongjy_parse, 'wzpt': wzpt_parse}
DISCOVERERS = {'nongjy': nongjy_discover, 'wzpt': wzpt_discover}
