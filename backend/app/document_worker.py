"""File-only extraction worker. Deploy in the network-disabled extraction container."""
import hashlib,json,re,subprocess,tempfile,time,os,signal,shutil
from pathlib import Path

MAX_BYTES=5_000_000
MAX_PAGES=20
class ExtractionError(ValueError):pass


def limits():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))
    resource.setrlimit(resource.RLIMIT_FSIZE,(8_000_000,8_000_000))
    if os.name=='posix' and __import__('sys').platform!='darwin':resource.setrlimit(resource.RLIMIT_AS,(512_000_000,512_000_000))


def tool(args,folder,deadline):
    timeout=min(20,max(0,deadline-time.monotonic()))
    if timeout<=0:raise ExtractionError('附件处理超过总时限')
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as error:
        process=subprocess.Popen(args,cwd=folder,stdout=output,stderr=error,start_new_session=True,preexec_fn=limits)
        try:process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait();raise ExtractionError('附件处理超时')
        if process.returncode:raise ExtractionError('附件处理工具拒绝或无法解析文件')
        output.seek(0);data=output.read(500_001)
        if len(data)>500_000:raise ExtractionError('提取文本超过限制')
        return data.decode('utf-8',errors='replace')


def extract(data,format):
    if len(data)>MAX_BYTES:raise ExtractionError('附件超过5MB限制')
    if format=='docx':
        from .attachments import docx_review_text
        text,has_body=docx_review_text(data)
        return [{'page':None,'position':'DOCX正文段与表格行' if has_body else 'DOCX表格行','method':'docx_text' if has_body else 'docx_table','text':text}]
    if format!='pdf' or not data.startswith(b'%PDF-'):raise ExtractionError('只支持PDF或DOCX签名')
    required=('pdfinfo','pdftotext')
    if any(not shutil.which(name) for name in required):raise ExtractionError('PDF文字提取工具未配置，请使用隔离提取容器')
    with tempfile.TemporaryDirectory(prefix='leaseradar-extract-') as folder:
        root=Path(folder);(root/'input.pdf').write_bytes(data);deadline=time.monotonic()+120
        info=tool(['pdfinfo','input.pdf'],folder,deadline)
        if re.search(r'^Encrypted:\s+yes',info,re.M):raise ExtractionError('不处理加密PDF')
        match=re.search(r'^Pages:\s+(\d+)',info,re.M)
        if not match or not 1<=int(match[1])<=MAX_PAGES:raise ExtractionError('PDF页数无法核验或超过20页')
        pages=[]
        for page in range(1,int(match[1])+1):
            text=tool(['pdftotext','-f',str(page),'-l',str(page),'-layout','input.pdf','-'],folder,deadline).strip()
            method='pdf_text'
            if not text:
                if any(not shutil.which(name) for name in ('pdftoppm','tesseract')):
                    raise ExtractionError(f'PDF第{page}页无文字层且OCR工具未配置；请使用隔离提取容器')
                tool(['pdftoppm','-f',str(page),'-l',str(page),'-singlefile','-scale-to','1600','-png','input.pdf','page'],folder,deadline)
                text=tool(['tesseract','page.png','stdout','-l','chi_sim+eng','--psm','6'],folder,deadline).strip();method='ocr_review'
                if not text:raise ExtractionError(f'PDF第{page}页OCR未识别到文字；不能作为已提取结果')
            if len(text)>20000:raise ExtractionError('单页文本超过限制')
            pages.append({'page':page,'position':f'PDF第{page}页','method':method,'text':text})
        return pages


def process_one(queue):
    queue=Path(queue);results=queue/'results';results.mkdir(exist_ok=True)
    for request in sorted((queue/'requests').glob('*.json')):
        if not re.fullmatch(r'\d+\.json',request.name):continue
        target=results/request.name
        if target.exists():continue
        result={'sha256':None,'format':None,'pages':[],'state':'failed','error':None}
        try:
            if request.is_symlink() or request.stat().st_size>1000:raise ExtractionError('请求文件边界无效')
            spec=json.loads(request.read_text())
            if not isinstance(spec,dict):raise ExtractionError('请求结构无效')
            digest=spec.get('sha256');format=spec.get('format')
            if not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest) or format not in ('pdf','docx'):raise ExtractionError('请求身份无效')
            result.update(sha256=digest,format=format)
            source=queue/'inputs'/f'{digest}.{format}'
            if source.is_symlink() or source.stat().st_size>MAX_BYTES:raise ExtractionError('附件文件边界无效')
            data=source.read_bytes()
            if hashlib.sha256(data).hexdigest()!=digest:raise ExtractionError('附件哈希不一致')
            result['pages']=extract(data,format);result['state']='review';result['error']=None
        except Exception as exc:result['error']=str(exc)[:200]
        temp=target.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False));temp.replace(target)
        return True
    return False


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--queue',default='/queue');parser.add_argument('--once',action='store_true');args=parser.parse_args()
    while True:
        process_one(args.queue)
        if args.once:break
        time.sleep(5)
if __name__=='__main__':main()
