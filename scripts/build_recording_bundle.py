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
    'scripts/verify_recording_bundle.py',
    'fixtures/replay/nongjy.html', 'frontend/index.html', 'frontend/app.js',
    'frontend/style.css', 'LICENSE',
    'docs/COMPETITION_DEMO.md', 'docs/submission/RECORDING_SCRIPT.md',
    'output/pdf/LeaseRadar_Competition_Intro_Draft.pdf',
    'docs/submission/assets/synthetic-comparison.png',
    'docs/submission/RELEASE_EVIDENCE.json',
)
TREES = ('backend/app', 'backend/migrations')
VIDEO = 'output/video/LeaseRadar_Storyboard_Review_20261024.mp4'
VIDEO_PROOF = 'output/video/LeaseRadar_Storyboard_Review_20261024.proof.json'
BROWSER_VIDEO = 'output/video/LeaseRadar_Browser_Walkthrough_20261026.webm'
BROWSER_PROOF = 'output/video/LeaseRadar_Browser_Walkthrough_20261026.proof.json'
BROWSER_REVIEW = 'output/video/LeaseRadar_Browser_Review_20261027.mp4'
BROWSER_REVIEW_PROOF = 'output/video/LeaseRadar_Browser_Review_20261027.proof.json'
BROWSER_REVIEW_MEDIA = 'output/video/LeaseRadar_Browser_Review_20261027.media.json'
BROWSER_NARRATION = 'docs/submission/BROWSER_NARRATION_20261027.json'
FULL_FILES = (
    'README.md', 'SECURITY.md', 'docs/DATA_POLICY.md',
    'docs/COMPETITION_REQUIREMENTS.md',
    'docs/submission/README.md', 'docs/submission/VIDEO_DRAFT.md',
    'docs/submission/PDF_REVIEW_20261025.md',
    'docs/submission/VIDEO_LISTENING_CHECKLIST_20261025.md',
    'docs/submission/BROWSER_WALKTHROUGH_20261026.md',
    'docs/submission/BROWSER_REVIEW_VIDEO_20261027.md',
    'docs/submission/DEMO_FREEZE_REHEARSAL_20261025.md',
    'docs/submission/DEMO_MATERIALS_20261023.md',
    'docs/submission/VIDEO_STORYBOARD.json',
    'scripts/build_storyboard_video.py', 'scripts/render_storyboard_video.swift',
    'scripts/verify_storyboard_video.swift',
    'scripts/record_demo_browser.js', BROWSER_VIDEO, BROWSER_PROOF,
    'scripts/build_browser_review_video.py', 'scripts/render_browser_review_video.swift',
    BROWSER_NARRATION, BROWSER_REVIEW, BROWSER_REVIEW_PROOF, BROWSER_REVIEW_MEDIA,
    VIDEO, VIDEO_PROOF, 'output/video/LeaseRadar_Storyboard_Review_20261024.media.json',
    *(f'docs/submission/video-assets/{name}' for name in (
        '00-intro.jpg', '01-filter.jpg', '02-compare.jpg', '03-evidence.jpg',
        '04-unknown.jpg', '05-inbox.jpg', '06-followup.jpg',
        '07-blocked.jpg', '08-favorites.jpg')),
)
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
解压前可运行`python3 scripts/verify_recording_bundle.py 压缩包路径`核对清单、CRC和安全路径。
包中没有真实数据库、账号、真实原始公告或私人笔记。素材仅合成，不能宣称真实接通、业绩或邮件投递。
正式提交仍需视频导出、PDF终审、比赛要求/评审访问方式与发布授权核对。
'''
FULL_GUIDE = '''# LeaseRadar 本地完整审阅包

本包合并可运行合成DEMO、介绍PDF审阅稿和已导出的静态分镜视频草稿。
视频是合成UI截图与本机TTS旁白，不是连续录屏或最终审稿版本；全部演示数据为合成。
另附约56秒无音轨的自动化浏览器连续操作片段，用于审查七步流程；它也不是最终投稿视频。
另附55.8秒有声审阅稿：由前述连续录制画面转码、加明确标识和系统合成旁白，属于剪辑成品，不是人工实时操作或最终投稿视频。
此包没有真实公告、数据库、账号、私有笔记或密钥，也没有对外发布或正式提交证明。

使用Python 3.12/3.13，在解压后的本目录运行：

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
.venv/bin/python scripts/demo.py --port 8002
```

安装锁定依赖需要联网；安装完成后，合成DEMO初始化和运行不需访问外部来源。
终端显示本机地址与私有DEMO_GUIDE.md路径，账号仅在本机新生成的指南内。
端口占用可换其他空闲端口；过期路线需创建新DEMO，不修改系统时间或旧数据。
PDF在output/pdf，视频及原有校验元数据在output/video，边界见docs/submission/README.md。
MANIFEST.json列出每项字节数和SHA256，只是完整性清单，不是可信签名。
解压前可用`python3 scripts/verify_recording_bundle.py 压缩包路径`检查清单、CRC和安全路径；也可用仓库中同名脚本。
视频已导出但尚未逐字听审；正式比赛指引、评审访问、视频托管和提交均待确认。
'''


def read_safe(root, relative):
    path = root / relative
    # Reject links at every component, even links staying inside the repository.
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(root)):
        raise ValueError(f'拒绝符号链接：{relative}')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'缺少或不安全的必需文件：{relative}')
    return path.read_bytes()


def build(root, destination, include_video=False):
    root = Path(root).resolve()
    destination = Path(destination)
    selected = set(FILES)
    if include_video:
        selected.update(FULL_FILES)
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
    if include_video:
        video = payload[VIDEO]
        if len(video) < 12 or video[4:8] != b'ftyp':
            raise ValueError('视频MP4签名无效；请先核对媒体文件')
        proof = json.loads(payload[VIDEO_PROOF])
        media = json.loads(payload['output/video/LeaseRadar_Storyboard_Review_20261024.media.json'])
        decode = proof.get('decode_check') if isinstance(proof, dict) else None
        if (not isinstance(proof, dict) or not isinstance(decode, dict)
                or not isinstance(media, dict)
                or proof.get('app_version') != evidence['app_version']
                or proof.get('capture_kind') != 'static_ui_storyboard'
                or proof.get('synthetic') is not True or proof.get('continuous_recording') is not False
                or proof.get('bytes') != len(video)
                or proof.get('sha256') != hashlib.sha256(video).hexdigest()
                or proof.get('storyboard_sha256') != hashlib.sha256(payload['docs/submission/VIDEO_STORYBOARD.json']).hexdigest()
                or decode.get('full_decode') != 'passed'
                or media.get('capture_kind') != 'static_ui_storyboard'
                or not isinstance(media.get('duration'), (float, int))
                or not isinstance(decode.get('duration'), (float, int))
                or abs(media['duration'] - decode['duration']) > 0.1):
            raise ValueError('视频与解码证明不一致；拒绝打包')
        browser_video = payload[BROWSER_VIDEO]
        browser_proof = json.loads(payload[BROWSER_PROOF])
        if (not browser_video.startswith(b'\x1a\x45\xdf\xa3')
                or not isinstance(browser_proof, dict)
                or browser_proof.get('app_version') != evidence['app_version']
                or browser_proof.get('capture_kind') != 'automated_continuous_browser_session'
                or browser_proof.get('synthetic') is not True
                or browser_proof.get('continuous_recording') is not True
                or browser_proof.get('audio') is not False
                or browser_proof.get('credential_entry_recorded') is not False
                or browser_proof.get('external_requests_blocked') is not True
                or browser_proof.get('bytes') != len(browser_video)
                or browser_proof.get('sha256') != hashlib.sha256(browser_video).hexdigest()
                or not isinstance(browser_proof.get('steps'), list)
                or len(browser_proof['steps']) != 7
                or not isinstance(browser_proof.get('verification'), dict)
                or browser_proof['verification'].get('full_decode') != 'passed'):
            raise ValueError('浏览器操作视频与证明不一致；拒绝打包')
        review = payload[BROWSER_REVIEW]
        review_proof = json.loads(payload[BROWSER_REVIEW_PROOF])
        review_media = json.loads(payload[BROWSER_REVIEW_MEDIA])
        narration = json.loads(payload[BROWSER_NARRATION])
        decode = review_proof.get('decode_check') if isinstance(review_proof, dict) else None
        if (len(review) < 12 or review[4:8] != b'ftyp'
                or not isinstance(review_proof, dict) or not isinstance(review_media, dict)
                or not isinstance(narration, dict) or not isinstance(decode, dict)
                or narration.get('capture_kind') != 'edited_automated_browser_demo'
                or narration.get('synthetic') is not True
                or narration.get('source_sha256') != browser_proof['sha256']
                or review_proof.get('capture_kind') != 'edited_automated_browser_demo'
                or review_proof.get('synthetic') is not True
                or review_proof.get('continuous_source_recording') is not True
                or review_proof.get('edited') is not True
                or review_proof.get('system_narration') is not True
                or review_proof.get('human_listening_review') is not False
                or review_proof.get('ready_to_submit') is not False
                or review_proof.get('source_video_sha256') != browser_proof['sha256']
                or review_proof.get('narration_plan_sha256') != hashlib.sha256(payload[BROWSER_NARRATION]).hexdigest()
                or review_proof.get('sha256') != hashlib.sha256(review).hexdigest()
                or review_proof.get('bytes') != len(review)
                or review_proof.get('frame_count') != decode.get('decoded_video_frames')
                or decode.get('full_decode') != 'passed'
                or decode.get('human_listening_review') is not False
                or not isinstance(decode.get('audio_peak'), (int, float)) or decode['audio_peak'] <= 0.01
                or review_media.get('capture_kind') != 'edited_automated_browser_demo'
                or not isinstance(review_media.get('duration'), (int, float))
                or abs(review_media['duration'] - decode.get('duration', 0)) > 0.1):
            raise ValueError('有声浏览器审阅稿与证明不一致；拒绝打包')
    payload['START_HERE.md'] = (FULL_GUIDE if include_video else GUIDE).encode()
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    dirty = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'], capture_output=True, text=True)
    manifest = {
        'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'source_commit': revision.stdout.strip() if revision.returncode == 0 else None,
        'working_tree_dirty': bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
        'mode': 'synthetic_demo_review_bundle' if include_video else 'synthetic_demo',
        'ready_to_submit': False,
        'app_version': evidence['app_version'],
        'evidence_commit': evidence.get('implementation_commit'),
        'video_capture_kind': ['static_ui_storyboard', 'automated_continuous_browser_session',
                               'edited_automated_browser_demo'] if include_video else None,
        'remaining': (['video_listening_and_final_form', 'pdf_final_review',
                       'contest_rules_and_repository_access', 'authorized_submission']
                      if include_video else
                      ['video_export', 'pdf_final_review', 'contest_rules_and_repository_access',
                       'authorized_submission']),
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
    parser.add_argument('--include-video', action='store_true', help='加入静态分镜视频与校验依据，生成完整本地审阅包')
    args = parser.parse_args()
    try:
        manifest = build(ROOT, args.output, include_video=args.include_video)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'录制包生成失败：{exc}\n')
    state = '静态分镜视频已纳入、待最终听审' if args.include_video else '视频未纳入'
    print(f'已生成合成演示包：{args.output}；{len(manifest["files"])}个文件；{state}，尚不可提交。')


if __name__ == '__main__':
    main()
