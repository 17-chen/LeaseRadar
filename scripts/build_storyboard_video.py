#!/usr/bin/env python3
"""Build an explicitly labelled static UI storyboard, using macOS local TTS/AVFoundation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def validate(story,assets):
    if not isinstance(story,dict) or story.get('capture_kind')!='static_ui_storyboard' or story.get('synthetic') is not True:
        raise ValueError('必须明确标注合成静态分镜')
    scenes=story.get('scenes')
    if not isinstance(scenes,list) or not 1<=len(scenes)<=20:raise ValueError('分镜数量无效')
    for scene in scenes:
        if not isinstance(scene,dict):raise ValueError('分镜结构无效')
        name=scene.get('image')
        if not isinstance(name,str) or Path(name).name!=name or Path(name).suffix not in ('.png','.jpg'):raise ValueError('分镜图片只允许同目录PNG/JPEG')
        path=assets/name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(assets.resolve()):raise ValueError('分镜图片缺失或不安全')
        signature=b'\x89PNG\r\n\x1a\n' if name.endswith('.png') else b'\xff\xd8\xff'
        if not path.read_bytes().startswith(signature):raise ValueError('图片签名与扩展名不一致')
        for key,maximum in [('title',50),('caption',160),('narration',600)]:
            if not isinstance(scene.get(key),str) or not 1<=len(scene[key].strip())<=maximum:raise ValueError('分镜文字无效')
    return scenes

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='新MP4路径，拒绝覆盖')
    parser.add_argument('--module-cache',type=Path,default=ROOT/'private/storyboard-module-cache',help='本地Swift模块缓存，不入Git')
    args=parser.parse_args()
    if args.output.exists():parser.error('拒绝覆盖已有视频，请使用新路径')
    storyboard_path=ROOT/'docs/submission/VIDEO_STORYBOARD.json'
    storyboard_bytes=storyboard_path.read_bytes()
    story=json.loads(storyboard_bytes)
    assets=ROOT/'docs/submission/video-assets';scenes=validate(story,assets)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='storyboard-',dir=ROOT/'private'))
    prepared=[]
    for i,scene in enumerate(scenes):
        text=work/f'{i:02d}.txt';text.write_text(scene['narration'])
        voice=work/f'{i:02d}.aiff'
        subprocess.run(['/usr/bin/say','-v','Tingting','-r','190','-f',str(text),'-o',str(voice)],check=True,timeout=60)
        encoded=voice.with_suffix('.m4a')
        subprocess.run(['/usr/bin/afconvert','-f','m4af','-d','aac',str(voice),str(encoded)],check=True,timeout=60)
        prepared.append({**scene,'image':str(assets/scene['image']),'audio':str(encoded)})
    manifest=work/'render.json';manifest.write_text(json.dumps({'scenes':prepared},ensure_ascii=False))
    binary=work/'render-video'
    subprocess.run(['xcrun','swiftc','-parse-as-library','-module-cache-path',str(args.module_cache.resolve()),str(ROOT/'scripts/render_storyboard_video.swift'),'-o',str(binary)],check=True,timeout=180)
    render=subprocess.run([str(binary),str(manifest),str(args.output.resolve())],capture_output=True,text=True,timeout=300)
    recovered=False
    if render.returncode:
        (work/'first-render-error.log').write_text(render.stdout+'\n'+render.stderr)
        silent=work/'silent.mp4'
        if not silent.exists() or silent.stat().st_size<1000:raise RuntimeError(f'视频编码失败，保留现场：{work}')
        if args.output.exists():args.output.rename(work/'failed-export.mp4')
        subprocess.run([str(binary),'--mux',str(manifest),str(silent),str(args.output.resolve())],check=True,timeout=120)
        recovered=True
    verify=work/'verify-video'
    subprocess.run(['xcrun','swiftc','-parse-as-library','-module-cache-path',str(args.module_cache.resolve()),str(ROOT/'scripts/verify_storyboard_video.swift'),'-o',str(verify)],check=True,timeout=180)
    qa=work/'qa'
    subprocess.run([str(verify),str(args.output.resolve()),str(qa)],check=True,timeout=180)
    proof={'app_version':story['app_version'],'source_commit':story['source_commit'],'capture_kind':story['capture_kind'],
           'synthetic':True,'tts_voice':'macOS Tingting','continuous_recording':False,'ready_to_submit':False,
           'storyboard_sha256':hashlib.sha256(storyboard_bytes).hexdigest(),
           'scene_images':{s['image']:hashlib.sha256((assets/s['image']).read_bytes()).hexdigest() for s in scenes},
           'decode_check':json.loads((qa/'decode-proof.json').read_text()),'mux_recovery_used':recovered,
           'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'bytes':args.output.stat().st_size}
    args.output.with_suffix('.proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
    print(json.dumps({'output':str(args.output),'work':str(work),'bytes':proof['bytes'],'capture_kind':proof['capture_kind']},ensure_ascii=False))

if __name__=='__main__':main()
