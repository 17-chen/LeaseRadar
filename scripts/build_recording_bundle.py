#!/usr/bin/env python3
"""Build a local recording handoff from an explicit allowlist, never private data."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'backend/alembic.ini', 'backend/requirements.lock', 'scripts/demo.py',
    'fixtures/replay/nongjy.html', 'frontend/index.html', 'frontend/app.js',
    'frontend/style.css', 'LICENSE',
    'docs/COMPETITION_DEMO.md', 'docs/submission/RECORDING_SCRIPT.md',
    'output/pdf/LeaseRadar_Competition_Intro_Draft.pdf',
    'docs/submission/assets/synthetic-comparison.png',
    'docs/submission/RELEASE_EVIDENCE.json',
)
TREES = ('backend/app', 'backend/migrations')
GUIDE = '''# LeaseRadar 本地录制包

这是合成演示录制素材，不是已提交作品或生产部署。介绍PDF为0.1.16审阅稿。
静态分镜视频草稿在仓库output/video另行交付，不包含在这个小型运行包中；最终视频尚未完成。
使用 Python 3.12/3.13。在解压后的本目录执行：

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
.venv/bin/python scripts/demo.py --port 8002
```

安装依赖需要联网；演示数据初始化与运行不需要外部来源或邮件。
浏览器打开终端显示的本机地址；随机账号在新生成的私有DEMO_GUIDE.md中。
登录后点击“开始演示”，依照 docs/submission/RECORDING_SCRIPT.md 录制。
macOS/Linux命令如上；Windows使用 .venv\\Scripts\\python 替代 .venv/bin/python。
停止用Ctrl+C。重新录制时再运行命令，旧数据不覆盖；不要共享新生成的private目录。
若端口占用用 --port 8003。若七步路线提示过期，创建新的DEMO，不修改系统时间。

运行前可核对MANIFEST.json中的SHA256；它是完整性记录，不是数字签名或可信发布证明。
包中没有真实数据库、账号、真实原始公告或私人笔记。素材仅合成，不能宣称真实接通、业绩或邮件投递。
正式提交仍需视频导出、PDF终审、比赛要求/评审访问方式与发布授权核对。
'''


def read_safe(root, relative):
    path = root / relative
    # Reject links at every component, even links staying inside the repository.
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(root)):
        raise ValueError(f'拒绝符号链接：{relative}')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'缺少或不安全的必需文件：{relative}')
    return path.read_bytes()


def build(root, destination):
    root = Path(root).resolve()
    destination = Path(destination)
    selected = set(FILES)
    for tree in TREES:
        base = root / tree
        if base.is_symlink() or not base.is_dir():
            raise ValueError(f'缺少或不安全的代码目录：{tree}')
        for path in base.rglob('*'):
            if path.is_symlink():
                raise ValueError(f'代码目录含符号链接：{path.relative_to(root)}')
            if path.is_file() and path.suffix == '.py':
                selected.add(path.relative_to(root).as_posix())
    payload = {name: read_safe(root, name) for name in sorted(selected)}
    evidence=json.loads(payload['docs/submission/RELEASE_EVIDENCE.json'])
    match=re.search(r"FastAPI\([^\n]+version=['\"]([^'\"]+)['\"]", payload['backend/app/main.py'].decode())
    if not isinstance(evidence,dict) or not match or evidence.get('app_version')!=match.group(1):
        raise ValueError('材料版本与应用版本不一致；请刷新并审查PDF和口播')
    if not payload['output/pdf/LeaseRadar_Competition_Intro_Draft.pdf'].startswith(b'%PDF-'):
        raise ValueError('介绍PDF签名无效；请先重建材料')
    payload['START_HERE.md'] = GUIDE.encode()
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    dirty = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'], capture_output=True, text=True)
    manifest = {
        'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'source_commit': revision.stdout.strip() if revision.returncode == 0 else None,
        'working_tree_dirty': bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
        'mode': 'synthetic_demo', 'ready_to_submit': False,
        'app_version': evidence['app_version'],
        'evidence_commit': evidence.get('implementation_commit'),
        'remaining': ['video_export', 'pdf_final_review', 'contest_rules_and_repository_access', 'authorized_submission'],
        'files': {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in payload.items()},
    }
    payload['MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    # Validate all inputs before creating the output; exclusive create protects earlier evidence.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            archive.writestr(name, data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(buffer.getvalue())
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='新ZIP路径，拒绝覆盖已有文件')
    args = parser.parse_args()
    try:
        manifest = build(ROOT, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'录制包生成失败：{exc}\n')
    print(f'已生成合成录制包：{args.output}；{len(manifest["files"])}个文件；视频未完成，尚不可提交。')


if __name__ == '__main__':
    main()
