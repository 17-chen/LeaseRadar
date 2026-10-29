"""Recording archives must exclude private state and remain independently runnable."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('recording_bundle', ROOT/'scripts/build_recording_bundle.py')
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)
verifier_spec = importlib.util.spec_from_file_location('recording_verifier', ROOT/'scripts/verify_recording_bundle.py')
verifier = importlib.util.module_from_spec(verifier_spec)
verifier_spec.loader.exec_module(verifier)


def sample_root(tmp_path):
    root = tmp_path/'repo'
    for name in bundle.FILES:
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'%PDF-synthetic' if name.endswith('.pdf') else b'synthetic file')
    for tree in bundle.TREES:
        path = root/tree/'module.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# synthetic')
    (root/'backend/app/main.py').write_text("app = FastAPI(title='Synthetic', version='0.0.1')")
    (root/'docs/submission/RELEASE_EVIDENCE.json').write_text(json.dumps({'app_version':'0.0.1','implementation_commit':'synthetic'}))
    for name in ('private/demo.db', '.env', 'private/DEMO_GUIDE.md', 'backend/app/__pycache__/x.pyc'):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('SECRET_SENTINEL')
    return root


def add_sample_video(root):
    for name in bundle.FULL_FILES:
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(b'synthetic file')
    video = b'\x00\x00\x00\x18ftypisomsynthetic'
    (root/bundle.VIDEO).write_bytes(video)
    (root/bundle.VIDEO_PROOF).write_text(json.dumps({
        'app_version': '0.0.1', 'capture_kind': 'static_ui_storyboard',
        'synthetic': True, 'continuous_recording': False,
        'storyboard_sha256': hashlib.sha256((root/'docs/submission/VIDEO_STORYBOARD.json').read_bytes()).hexdigest(),
        'bytes': len(video), 'sha256': hashlib.sha256(video).hexdigest(),
        'decode_check': {'full_decode': 'passed', 'duration': 10.0},
    }))
    (root/'output/video/LeaseRadar_Storyboard_Review_20261024.media.json').write_text(json.dumps({
        'capture_kind': 'static_ui_storyboard', 'duration': 10.0,
    }))
    browser_video = b'\x1a\x45\xdf\xa3synthetic-browser-video'
    (root/bundle.BROWSER_VIDEO).write_bytes(browser_video)
    (root/bundle.BROWSER_PROOF).write_text(json.dumps({
        'app_version': '0.0.1', 'capture_kind': 'automated_continuous_browser_session',
        'synthetic': True, 'continuous_recording': True, 'audio': False,
        'credential_entry_recorded': False, 'external_requests_blocked': True,
        'bytes': len(browser_video), 'sha256': hashlib.sha256(browser_video).hexdigest(),
        'steps': list(range(7)), 'verification': {'full_decode': 'passed'},
    }))
    review = b'\x00\x00\x00\x18ftypisomsynthetic-review'
    (root/bundle.BROWSER_REVIEW).write_bytes(review)
    narration = {'capture_kind': 'edited_automated_browser_demo', 'synthetic': True,
                 'source_sha256': hashlib.sha256(browser_video).hexdigest()}
    (root/bundle.BROWSER_NARRATION).write_text(json.dumps(narration))
    (root/bundle.BROWSER_REVIEW_PROOF).write_text(json.dumps({
        'capture_kind': 'edited_automated_browser_demo', 'synthetic': True,
        'continuous_source_recording': True, 'edited': True, 'system_narration': True,
        'human_listening_review': False, 'ready_to_submit': False,
        'source_video_sha256': hashlib.sha256(browser_video).hexdigest(),
        'narration_plan_sha256': hashlib.sha256((root/bundle.BROWSER_NARRATION).read_bytes()).hexdigest(),
        'bytes': len(review), 'sha256': hashlib.sha256(review).hexdigest(),
        'frame_count': 558, 'decode_check': {'decoded_video_frames': 558,
            'full_decode': 'passed', 'human_listening_review': False,
            'audio_peak': 0.5, 'duration': 55.8},
    }))
    (root/bundle.BROWSER_REVIEW_MEDIA).write_text(json.dumps({
        'capture_kind': 'edited_automated_browser_demo', 'duration': 55.8,
    }))
    full = b'\x1a\x45\xdf\xa3synthetic-full-browser-video'
    (root/bundle.FULL_BROWSER_VIDEO).write_bytes(full)
    (root/bundle.FULL_BROWSER_PROOF).write_text(json.dumps({
        'app_version': '0.0.1', 'capture_kind': 'paced_automated_continuous_browser_session',
        'synthetic': True, 'continuous_recording': True, 'audio': False,
        'credential_entry_recorded': False, 'external_requests_blocked': True,
        'trim_seconds': 0, 'bytes': len(full), 'sha256': hashlib.sha256(full).hexdigest(),
        'observations': list(range(10)), 'verification': {'full_decode': 'passed'},
    }))
    long_review = b'\x00\x00\x00\x18ftypisomsynthetic-long-review'
    (root/bundle.FULL_BROWSER_REVIEW).write_bytes(long_review)
    full_plan = {'capture_kind': 'edited_full_automated_browser_demo', 'synthetic': True,
                 'source_sha256': hashlib.sha256(full).hexdigest(), 'segments': [
                     {'start_frame': i * 200, 'step': f'合成场景{i}', 'narration': '合成字幕。保留未知。'}
                     for i in range(10)]}
    (root/bundle.FULL_BROWSER_NARRATION).write_text(json.dumps(full_plan))
    (root/bundle.FULL_BROWSER_REVIEW_PROOF).write_text(json.dumps({
        'capture_kind': 'edited_full_automated_browser_demo', 'synthetic': True,
        'continuous_source_recording': True, 'edited': True, 'system_narration': True,
        'human_listening_review': False, 'ready_to_submit': False,
        'source_video_sha256': hashlib.sha256(full).hexdigest(),
        'narration_plan_sha256': hashlib.sha256((root/bundle.FULL_BROWSER_NARRATION).read_bytes()).hexdigest(),
        'bytes': len(long_review), 'sha256': hashlib.sha256(long_review).hexdigest(),
        'frame_count': 2076, 'decode_check': {'decoded_video_frames': 2076,
            'full_decode': 'passed', 'human_listening_review': False,
            'audio_peak': 0.5, 'duration': 207.6},
    }))
    (root/bundle.FULL_BROWSER_REVIEW_MEDIA).write_text(json.dumps({
        'capture_kind': 'edited_full_automated_browser_demo', 'duration': 207.6,
        'fps': 10, 'width': 1280, 'height': 840, 'timeline': [
            {'start': i * 20, 'step': f'合成场景{i}', 'audio_duration': 10}
            for i in range(10)],
    }))
    captions, transcript = bundle.caption_builder.render(*[
        (root / name).read_bytes() for name in (
            bundle.FULL_BROWSER_NARRATION, bundle.FULL_BROWSER_REVIEW_MEDIA,
            bundle.FULL_BROWSER_REVIEW_PROOF)])
    (root/bundle.caption_builder.CAPTIONS).write_bytes(captions)
    (root/bundle.caption_builder.TRANSCRIPT).write_bytes(transcript)


@pytest.mark.parametrize('name', [bundle.caption_builder.CAPTIONS, bundle.caption_builder.TRANSCRIPT])
def test_full_bundle_rejects_stale_captions(tmp_path, name):
    root = sample_root(tmp_path)
    add_sample_video(root)
    (root/name).write_bytes((root/name).read_bytes() + b'changed')
    destination = tmp_path/'stale-captions.zip'
    with pytest.raises(ValueError, match='字幕或逐段稿'):
        bundle.build(root, destination, include_video=True)
    assert not destination.exists()


def test_allowlist_and_hashes_exclude_private_state(tmp_path):
    root = sample_root(tmp_path)
    archive = tmp_path/'recording.zip'
    result = bundle.build(root, archive)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        manifest = json.loads(z.read('MANIFEST.json'))
        assert set(z.namelist()) == set(manifest['files']) | {'MANIFEST.json'}
        assert manifest['mode'] == 'synthetic_demo' and not manifest['ready_to_submit']
        assert 'video_export' in manifest['remaining'] and result == manifest
        for name, entry in manifest['files'].items():
            data = z.read(name)
            assert b'SECRET_SENTINEL' not in data
            assert entry == {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        assert 'backend/app/module.py' in z.namelist()
    assert verifier.verify(archive) == manifest


def test_verifier_rejects_unsafe_or_modified_archive(tmp_path):
    root = sample_root(tmp_path)
    archive = tmp_path/'recording.zip'
    bundle.build(root, archive)
    with zipfile.ZipFile(archive) as source:
        payload = {name: source.read(name) for name in source.namelist()}
    for case in ('modified', 'traversal', 'duplicate', 'symlink'):
        unsafe = tmp_path/f'{case}.zip'
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message="Duplicate name: 'frontend/app.js'", category=UserWarning)
            with zipfile.ZipFile(unsafe, 'w') as destination:
                for name, data in payload.items():
                    if case == 'modified' and name == 'frontend/app.js':
                        data = b'changed'
                    destination.writestr(name, data)
                if case == 'traversal':
                    destination.writestr('../outside', b'bad')
                elif case == 'duplicate':
                    destination.writestr('frontend/app.js', b'bad')
                elif case == 'symlink':
                    import stat
                    link = zipfile.ZipInfo('link')
                    link.create_system = 3
                    link.external_attr = (stat.S_IFLNK | 0o777) << 16
                    destination.writestr(link, 'target')
        with pytest.raises(ValueError, match='哈希|大小|路径|条目'):
            verifier.verify(unsafe)


def test_existing_archive_is_preserved(tmp_path):
    root = sample_root(tmp_path)
    archive = tmp_path/'existing.zip'
    archive.write_bytes(b'previous evidence')
    with pytest.raises(FileExistsError):
        bundle.build(root, archive)
    assert archive.read_bytes() == b'previous evidence'


def test_stale_material_version_cannot_be_packaged(tmp_path):
    root = sample_root(tmp_path)
    (root/'docs/submission/RELEASE_EVIDENCE.json').write_text(json.dumps({'app_version':'old'}))
    with pytest.raises(ValueError, match='版本不一致'):
        bundle.build(root, tmp_path/'stale.zip')
    assert not (tmp_path/'stale.zip').exists()


@pytest.mark.parametrize('parent_link', [False, True])
def test_symlinks_cannot_import_private_files(tmp_path, parent_link):
    root = sample_root(tmp_path)
    if parent_link:
        path = root/'backend/app'
        path.rename(root/'original-app')
        path.symlink_to(root/'private', target_is_directory=True)
    else:
        path = root/'frontend/app.js'
        path.unlink()
        path.symlink_to(root/'private/DEMO_GUIDE.md')
    with pytest.raises(ValueError, match='符号链接|不安全'):
        bundle.build(root, tmp_path/'rejected.zip')
    assert not (tmp_path/'rejected.zip').exists()


def test_missing_material_fails_without_partial_archive(tmp_path):
    root = sample_root(tmp_path)
    (root/'output/pdf/LeaseRadar_Competition_Intro_Draft.pdf').unlink()
    with pytest.raises(ValueError, match='必需文件'):
        bundle.build(root, tmp_path/'missing.zip')
    assert not (tmp_path/'missing.zip').exists()


def test_full_review_bundle_contains_verified_video_and_excludes_private(tmp_path):
    root = sample_root(tmp_path)
    add_sample_video(root)
    archive = tmp_path/'full.zip'
    bundle.build(root, archive, include_video=True)
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('MANIFEST.json'))
        assert z.testzip() is None
        assert manifest['mode'] == 'synthetic_demo_review_bundle'
        assert manifest['video_capture_kind'] == [
            'static_ui_storyboard', 'automated_continuous_browser_session',
            'edited_automated_browser_demo', 'paced_automated_continuous_browser_session',
            'edited_full_automated_browser_demo']
        assert bundle.BROWSER_VIDEO in z.namelist()
        assert bundle.BROWSER_REVIEW in z.namelist()
        assert bundle.FULL_BROWSER_VIDEO in z.namelist()
        assert bundle.FULL_BROWSER_REVIEW in z.namelist()
        assert not manifest['ready_to_submit']
        assert 'video_listening_and_final_form' in manifest['remaining']
        assert 'video_export' not in manifest['remaining']
        assert set(z.namelist()) == set(manifest['files']) | {'MANIFEST.json'}
        assert set(bundle.FULL_FILES).issubset(z.namelist())
        assert b'SECRET_SENTINEL' not in b''.join(z.read(name) for name in z.namelist())
        for name, entry in manifest['files'].items():
            data = z.read(name)
            assert entry == {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


@pytest.mark.parametrize('damage', ['video', 'proof', 'storyboard', 'missing'])
def test_full_bundle_rejects_missing_or_unverified_video(tmp_path, damage):
    root = sample_root(tmp_path)
    add_sample_video(root)
    if damage == 'video':
        (root/bundle.VIDEO).write_bytes(b'not an mp4')
    elif damage == 'proof':
        proof = json.loads((root/bundle.VIDEO_PROOF).read_text())
        proof['sha256'] = '0' * 64
        (root/bundle.VIDEO_PROOF).write_text(json.dumps(proof))
    elif damage == 'storyboard':
        (root/'docs/submission/VIDEO_STORYBOARD.json').write_text('changed after export')
    else:
        (root/bundle.VIDEO).unlink()
    archive = tmp_path/'rejected.zip'
    with pytest.raises(ValueError, match='视频|必需文件'):
        bundle.build(root, archive, include_video=True)
    assert not archive.exists()


@pytest.mark.parametrize('damage', ['browser_video', 'browser_proof', 'browser_missing'])
def test_full_bundle_rejects_unverified_browser_walkthrough(tmp_path, damage):
    root = sample_root(tmp_path)
    add_sample_video(root)
    if damage == 'browser_video':
        (root/bundle.BROWSER_VIDEO).write_bytes(b'not a webm')
    elif damage == 'browser_proof':
        proof = json.loads((root/bundle.BROWSER_PROOF).read_text())
        proof['audio'] = True
        (root/bundle.BROWSER_PROOF).write_text(json.dumps(proof))
    else:
        (root/bundle.BROWSER_VIDEO).unlink()
    archive = tmp_path/'rejected-browser.zip'
    with pytest.raises(ValueError, match='浏览器操作视频|必需文件'):
        bundle.build(root, archive, include_video=True)
    assert not archive.exists()


@pytest.mark.parametrize('damage', ['review_video', 'review_proof', 'narration', 'audio_proof'])
def test_full_bundle_rejects_stale_or_silent_browser_review(tmp_path, damage):
    root = sample_root(tmp_path)
    add_sample_video(root)
    if damage == 'review_video':
        (root/bundle.BROWSER_REVIEW).write_bytes(b'not mp4')
    elif damage == 'narration':
        (root/bundle.BROWSER_NARRATION).write_text('{}')
    else:
        proof = json.loads((root/bundle.BROWSER_REVIEW_PROOF).read_text())
        if damage == 'review_proof':
            proof['ready_to_submit'] = True
        else:
            proof['decode_check']['audio_peak'] = 0.0
        (root/bundle.BROWSER_REVIEW_PROOF).write_text(json.dumps(proof))
    archive = tmp_path/'rejected-review.zip'
    with pytest.raises(ValueError, match='有声浏览器审阅稿'):
        bundle.build(root, archive, include_video=True)
    assert not archive.exists()


@pytest.mark.parametrize('damage', ['source', 'source_proof', 'narration', 'silent_review'])
def test_full_bundle_rejects_invalid_ten_scene_media(tmp_path, damage):
    root = sample_root(tmp_path)
    add_sample_video(root)
    if damage == 'source':
        (root/bundle.FULL_BROWSER_VIDEO).write_bytes(b'changed')
    elif damage == 'source_proof':
        proof = json.loads((root/bundle.FULL_BROWSER_PROOF).read_text())
        proof['trim_seconds'] = 1.8
        (root/bundle.FULL_BROWSER_PROOF).write_text(json.dumps(proof))
    elif damage == 'narration':
        (root/bundle.FULL_BROWSER_NARRATION).write_text('{}')
    else:
        proof = json.loads((root/bundle.FULL_BROWSER_REVIEW_PROOF).read_text())
        proof['decode_check']['audio_peak'] = 0
        (root/bundle.FULL_BROWSER_REVIEW_PROOF).write_text(json.dumps(proof))
    archive = tmp_path/'rejected-ten-scene.zip'
    with pytest.raises(ValueError, match='十场景'):
        bundle.build(root, archive, include_video=True)
    assert not archive.exists()


@pytest.mark.parametrize('include_video', [False, True])
def test_actual_archive_initializes_and_serves_without_original_repository(tmp_path, include_video):
    archive = tmp_path/'actual.zip'
    bundle.build(ROOT, archive, include_video=include_video)
    unpacked = tmp_path/'unpacked'
    with zipfile.ZipFile(archive) as z:
        z.extractall(unpacked)
    script = '''
import socket,re
def forbidden(*a,**k): raise AssertionError('unexpected external network')
socket.socket.connect=forbidden
from app.demo import prepare
from app.config import DATA
proof=prepare()
assert (proof['listings'],proof['versions'],proof['inbox'])==(6,7,5)
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
password=re.search(r'密码：([^\\n]+)',(DATA/'DEMO_GUIDE.md').read_text()).group(1)
login=client.post('/api/v1/auth/login',json={'username':'demo','password':password})
assert login.status_code==200
client.headers['X-CSRF-Token']=login.json()['csrf']
assert client.get('/api/v1/demo/scenario').status_code==200
assert client.get('/').status_code==200
assert client.get('/static/style.css').status_code==200
assert client.get('/static/app.js').status_code==200
r=client.post('/api/v1/listings/search',json={'filters':{'area_m2_min':'30','first_year_monthly_max':'12000','registration_open':True}})
assert r.status_code==200 and r.json()['total']==4
'''
    data = tmp_path/'isolated-data'
    env = {**os.environ, 'PYTHONPATH': str(unpacked/'backend'), 'APP_MODE': 'demo',
           'DATA_DIR': str(data), 'DATABASE_URL': 'sqlite:///'+str(data/'demo.db'),
           'EMAIL_ENABLED': 'false', 'SOURCE_ALERT_EMAIL_ENABLED': 'false',
           'SOURCE_DOCUMENTS_ENABLED': 'false', 'SOURCE_DOCUMENT_DOWNLOADS_ENABLED': 'false'}
    result = subprocess.run([sys.executable, '-c', script], cwd=unpacked, env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout+result.stderr
