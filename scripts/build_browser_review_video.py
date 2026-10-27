#!/usr/bin/env python3
"""Add local synthetic narration to the verified continuous browser demo for review."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'docs/submission/BROWSER_NARRATION_20261027.json'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='新MP4路径，拒绝覆盖')
    parser.add_argument('--ffmpeg', type=Path, default=Path(os.environ.get('PLAYWRIGHT_FFMPEG',
        '/Users/chenxin/Library/Caches/ms-playwright/ffmpeg-1011/ffmpeg-mac')))
    args = parser.parse_args()
    output = args.output.resolve()
    if output.suffix.lower() != '.mp4' or output.exists() or output.with_suffix('.media.json').exists():
        parser.error('输出必须是不存在的新MP4文件')
    if not args.ffmpeg.is_file():
        parser.error('需要Playwright随附的ffmpeg，用--ffmpeg指定')
    plan_bytes = PLAN.read_bytes()
    plan = json.loads(plan_bytes)
    source = ROOT / plan['source_video']
    proof = source.with_suffix('.proof.json')
    source_proof = json.loads(proof.read_text())
    if (plan['capture_kind'] != 'edited_automated_browser_demo' or plan['synthetic'] is not True
            or source_proof['capture_kind'] != 'automated_continuous_browser_session'
            or source_proof['synthetic'] is not True
            or source_proof['audio'] is not False
            or sha256(source) != plan['source_sha256']
            or sha256(source) != source_proof['sha256']):
        raise ValueError('浏览器原片/证明不匹配或非合成场景')
    segments = plan['segments']
    if len(segments) != 8 or [s['start_frame'] for s in segments] != [0, 22, 97, 172, 247, 322, 397, 485]:
        raise ValueError('旁白时间线无效')
    for segment in segments:
        if not 1 <= len(segment['narration']) <= 100 or not 1 <= len(segment['step']) <= 30:
            raise ValueError('旁白文字无效')
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='browser-review-', dir=ROOT / 'private'))
    frames = work / 'frames'
    frames.mkdir()
    subprocess.run([str(args.ffmpeg), '-hide_banner', '-loglevel', 'error', '-i', str(source),
                    '-r', '10', str(frames / 'frame-%05d.png')], check=True, timeout=120)
    frame_count = len(list(frames.glob('frame-*.png')))
    if not 500 <= frame_count <= 600:
        raise ValueError(f'抽帧数异常：{frame_count}，保留现场 {work}')
    rendered = []
    for i, segment in enumerate(segments):
        script = work / f'{i:02d}.txt'
        script.write_text(segment['narration'])
        aiff = script.with_suffix('.aiff')
        m4a = script.with_suffix('.m4a')
        subprocess.run(['/usr/bin/say', '-v', 'Tingting', '-r', '190', '-f', str(script), '-o', str(aiff)],
                       check=True, timeout=30)
        subprocess.run(['/usr/bin/afconvert', '-f', 'm4af', '-d', 'aac', str(aiff), str(m4a)],
                       check=True, timeout=30)
        rendered.append({**segment, 'audio': str(m4a)})
    manifest = work / 'render.json'
    manifest.write_text(json.dumps({'frames': str(frames), 'frame_count': frame_count,
                                    'segments': rendered}, ensure_ascii=False))
    cache = ROOT / 'private/browser-review-swift-cache'
    binary = work / 'render-video'
    subprocess.run(['xcrun', 'swiftc', '-parse-as-library', '-module-cache-path', str(cache),
                    str(ROOT / 'scripts/render_browser_review_video.swift'), '-o', str(binary)],
                   check=True, timeout=180)
    try:
        subprocess.run([str(binary), str(manifest), str(output)], check=True, timeout=300)
    except Exception:
        if output.exists():
            output.rename(work / 'failed-export.mp4')
        raise
    verify = work / 'verify-video'
    subprocess.run(['xcrun', 'swiftc', '-parse-as-library', '-module-cache-path', str(cache),
                    str(ROOT / 'scripts/verify_storyboard_video.swift'), '-o', str(verify)],
                   check=True, timeout=180)
    qa = work / 'qa'
    subprocess.run([str(verify), str(output), str(qa)], check=True, timeout=180)
    decoded = json.loads((qa / 'decode-proof.json').read_text())
    result = {
        'schema': 1, 'capture_kind': 'edited_automated_browser_demo', 'synthetic': True,
        'continuous_source_recording': True, 'edited': True, 'system_narration': True,
        'human_listening_review': False, 'ready_to_submit': False,
        'source_video': plan['source_video'], 'source_video_sha256': sha256(source),
        'source_commit': source_proof['source_commit'],
        'narration_plan_sha256': hashlib.sha256(plan_bytes).hexdigest(),
        'frame_count': frame_count, 'decode_check': decoded,
        'sha256': sha256(output), 'bytes': output.stat().st_size,
    }
    output.with_suffix('.proof.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'work': str(work), 'duration': decoded['duration'],
                      'sha256': result['sha256']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
