"""Bounded DOCX table extraction; no macros, external resources or embedded code."""
import hashlib
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal
from .collectors import stream_public, SourceError
from .config import DATA
import httpx

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def docx_tables(data):
    if len(data) > 20_000_000 or not data.startswith(b'PK'):
        raise SourceError('DOCX文件格式或大小不合规')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(e.file_size for e in entries) > 40_000_000:
            raise SourceError('DOCX展开大小超过限制')
        for entry in entries:
            if entry.flag_bits & 1 or entry.file_size > 10_000_000 or (entry.compress_size and entry.file_size / entry.compress_size > 150):
                raise SourceError('DOCX压缩结构不合规')
            if 'vbaProject' in entry.filename or '..' in entry.filename.split('/'):
                raise SourceError('拒绝宏或异常路径')
        xml = archive.read('word/document.xml')
        if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
            raise SourceError('拒绝XML外部实体')
        root = ET.fromstring(xml)
    return [[[''.join(t.text or '' for t in c.findall('.//w:t', NS)).strip() for c in row.findall('w:tc', NS)]
             for row in table.findall('w:tr', NS)] for table in root.findall('.//w:tbl', NS)]

def identity(text):
    return re.sub(r'\s+', '', re.sub(r'^标的\s*\d+\s*[：:]', '', text))

def enrich_tables(fields, evidence, tables, url):
    candidates = []
    for table_no, table in enumerate(tables, 1):
        if not table: continue
        headers = table[0]
        if '标的概况' not in headers or '首年租金起始价' not in headers: continue
        title_col, price_col = headers.index('标的概况'), headers.index('首年租金起始价')
        for row_no, row in enumerate(table[1:], 2):
            if len(row) <= max(title_col, price_col): continue
            if identity(row[title_col]) != identity(fields['title']): continue
            value = re.fullmatch(r'([\d,.]+)\s*(万元|元)', row[price_col])
            if value:
                amount = Decimal(value.group(1).replace(',', '')) * (10000 if value.group(2) == '万元' else 1)
                candidates.append((amount, f'DOCX表{table_no} 行{row_no} 列{price_col+1}：首年租金起始价 {row[price_col]}；标的 {row[title_col]}；来源 {url}'))
    amounts = {amount for amount, _ in candidates}
    if len(amounts) != 1: return False
    amount = next(iter(amounts))
    if fields.get('raw_amount') and Decimal(fields['raw_amount']) != amount:
        fields['warnings'].append('附件与页面价格冲突，保留原值，周期待核对')
        return False
    fields['period_basis'] = 'first_year'
    evidence['period_basis'] = candidates[0][1]
    fields['warnings'] = [w for w in fields['warnings'] if not w.startswith('价格周期尚未')]
    fields['warnings'].append('已核实首年租金口径；递增、免租期和费用未计算总成本')
    return True

def fetch_docx(url):
    with stream_public(url) as response:
        if response.status_code != 200: raise SourceError(f'附件HTTP {response.status_code}')
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > 20_000_000: raise SourceError('附件超过20MB限制')
    return bytes(data)

def enrich_docx(fields, evidence, cache):
    for attachment in fields.get('attachments', []):
        url = attachment['url']
        if not re.search(r'\.docx(?:\?|$)', url, re.I): continue
        try:
            if url not in cache:
                import time
                time.sleep(2.5)
                data = fetch_docx(url)
                tables = docx_tables(data)
                digest = hashlib.sha256(data).hexdigest()
                folder = DATA / 'snapshots'; folder.mkdir(exist_ok=True)
                (folder / (digest + '.docx')).write_bytes(data)
                cache[url] = (tables, digest)
            tables, digest = cache[url]
            attachment['sha256'] = digest
            if enrich_tables(fields, evidence, tables, url): return
        except Exception as exc:
            fields['warnings'].append('附件解析待复核：' + str(exc)[:100])
