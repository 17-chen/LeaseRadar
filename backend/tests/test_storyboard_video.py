"""Media input checks run without macOS speech, cameras, network, or encoders."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('storyboard',ROOT/'scripts/build_storyboard_video.py')
video=importlib.util.module_from_spec(spec);spec.loader.exec_module(video)

def story():
    return {'capture_kind':'static_ui_storyboard','synthetic':True,'scenes':[
        {'image':'a.jpg','title':'合成测试','caption':'静态分镜','narration':'合成旁白'}]}

def test_committed_storyboard_is_explicit_and_assets_exist():
    data=json.loads((ROOT/'docs/submission/VIDEO_STORYBOARD.json').read_text())
    assert len(video.validate(data,ROOT/'docs/submission/video-assets'))==10
    assert '非连续录屏' in data['scenes'][0]['caption']

@pytest.mark.parametrize('bad',[{'synthetic':False},{'capture_kind':'continuous_recording'},{'scenes':[]}])
def test_labels_and_scene_count_cannot_be_omitted(tmp_path,bad):
    with pytest.raises(ValueError):video.validate({**story(),**bad},tmp_path)

def test_paths_links_signatures_and_empty_speech_are_rejected(tmp_path):
    (tmp_path/'a.jpg').write_bytes(b'\xff\xd8\xffsynthetic')
    assert video.validate(story(),tmp_path)
    data=story();data['scenes'][0]['image']='../a.jpg'
    with pytest.raises(ValueError,match='同目录'):video.validate(data,tmp_path)
    data=story();data['scenes'][0]['narration']=' '
    with pytest.raises(ValueError,match='文字'):video.validate(data,tmp_path)
    (tmp_path/'a.jpg').write_bytes(b'not image')
    with pytest.raises(ValueError,match='签名'):video.validate(story(),tmp_path)
    (tmp_path/'a.jpg').unlink();(tmp_path/'a.jpg').symlink_to(tmp_path/'private.jpg')
    with pytest.raises(ValueError,match='不安全'):video.validate(story(),tmp_path)

def test_existing_video_is_not_overwritten_or_speech_started(tmp_path):
    output=tmp_path/'existing.mp4';output.write_bytes(b'previous recording')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/build_storyboard_video.py'),'--output',str(output)],capture_output=True,text=True,timeout=10)
    assert result.returncode!=0 and '拒绝覆盖' in result.stderr
    assert output.read_bytes()==b'previous recording'
