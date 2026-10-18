"""Verified HTML contracts; unknown values are deliberately preserved."""
import hashlib
import ipaddress
import re
import socket
import time
from datetime import datetime
from decimal import Decimal
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
import httpx
from contextlib import contextmanager
from bs4 import BeautifulSoup
from .config import ALLOWED_HOSTS

class SourceError(RuntimeError):
    def __init__(self, message, *, retryable=False, retry_after=None, blocked=False):
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after
        self.blocked = blocked

def response_error(response):
    """Keep Retry-After as a minimum delay, never retry blocked access."""
    from email.utils import parsedate_to_datetime
    from datetime import timezone
    delay = None
    value = response.headers.get('retry-after', '')
    try:
        delay = max(0, int(value))
    except ValueError:
        try:
            delay = max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            pass
    status = response.status_code
    return SourceError(f'HTTP {status}; 不自动绕过访问控制', retryable=status in (408, 429, 500, 502, 503, 504),
                       retry_after=delay, blocked=status in (401, 403))

def public_addresses(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise SourceError('URL不在已核准HTTPS来源范围')
    addresses = []
    for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise SourceError('拒绝非公网地址')
        if info[4][0] not in addresses: addresses.append(info[4][0])
    if not addresses: raise SourceError('来源未解析到公网地址')
    return sorted(addresses, key=lambda a: ipaddress.ip_address(a).version)

def validate_url(url):
    public_addresses(url)
    return url

@contextmanager
def stream_public(url):
    # Connect to the vetted IP itself; Host and TLS SNI still use the approved hostname.
    addresses = public_addresses(url)
    original = httpx.URL(url)
    pinned = original.copy_with(host=addresses[0])
    with httpx.Client(timeout=25, follow_redirects=False, trust_env=False,
                      headers={'User-Agent':'LeaseRadar/0.1 (public source research)', 'Host':original.host}) as client:
        with client.stream('GET', pinned, extensions={'sni_hostname':original.host}) as response:
            yield response

def fetch(url):
    # No redirects: new destinations must be explicitly reviewed.
    with stream_public(url) as response:
        if response.status_code != 200:
            raise response_error(response)
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

def location_parts(value):
    city = re.search(r'(?:^|省|自治区)([^省市区县]{2,8}市)', value)
    district = re.match(r'([^区县]{1,6}[区县])', value[city.end():]) if city else re.fullmatch(r'([^区县]{1,6}[区县])', value)
    name = district.group(1) if district else None
    if name and name.endswith(('社区', '开发区', '园区')): name = None
    return city.group(1) if city else None, name

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
              'period_basis': None, 'price_kind': None, 'status': 'unknown',
              'parser_version': 'nongjy-html-v3', 'warnings': []}
    evidence = {'title': fields['title']}
    for label, key in [('项目位置：', 'address'), ('项目编号：', 'project_code'), ('交易单位：', 'area_m2'), ('保证金：', 'deposit')]:
        node = next((n for n in soup.select('.cont-info-left-bt') if n.get_text(strip=True) == label), None)
        if node:
            value = node.parent.get_text(' ', strip=True).replace(label, '', 1).strip()
            evidence[key] = label + value
            if key in ('area_m2', 'deposit'):
                number = r'(?<![\d,.])(\d+(?:,\d{3})*(?:\.\d+)?)'
                unit = r'\s*(㎡|平方米)' if key == 'area_m2' else r'\s*(万元|元)'
                found = re.findall(number + unit, value)
                fields[key] = None
                if len(found) == 1:
                    amount = Decimal(found[0][0].replace(',', ''))
                    fields[key] = str(amount * (10000 if found[0][1] == '万元' else 1))
                if key == 'area_m2': fields['area_approx'] = '约' in value
            else:
                fields[key] = value
    amount = soup.select_one('.cont-info-left-timebox-price')
    if amount:
        value = amount.get_text(strip=True)
        if re.fullmatch(r'\d+(?:,\d{3})*(?:\.\d+)?', value):
            evidence['raw_amount'] = amount.parent.get_text(' ', strip=True)
            label = evidence['raw_amount']
            fields['raw_amount'] = str(Decimal(value.replace(',', '')) * (10000 if '万元' in label else 1)) if '元' in label else None
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
    fields['city'], fields['district'] = location_parts(address)
    for key in ('city', 'district'):
        if fields[key]: evidence[key] = '项目位置：' + address
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
    from .adapters.wzpt import parse
    return parse(html, url)

PARSERS = {'nongjy': nongjy_parse, 'wzpt': wzpt_parse}
DISCOVERERS = {'nongjy': nongjy_discover, 'wzpt': wzpt_discover}
