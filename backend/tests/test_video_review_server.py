"""Real loopback HTTP verifies byte ranges used by browser scene seeking."""
from functools import partial
from http.server import ThreadingHTTPServer
import importlib.util
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('review_server', ROOT/'scripts/serve_video_review.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


@pytest.mark.parametrize('value,expected', [('bytes=2-5', (2, 5)), ('bytes=7-', (7, 9)),
    ('bytes=-3', (7, 9)), ('bytes=1-999', (1, 9)), ('bytes=-999', (0, 9))])
def test_supported_byte_ranges(value, expected):
    assert server.byte_range(value, 10) == expected


@pytest.mark.parametrize('value', ['bytes=10-', 'bytes=5-2', 'bytes=-0', 'bytes=-',
    'bytes=0-1,4-5', 'bytes=x-2', 'items=1-2'])
def test_unsatisfiable_or_multiple_ranges_are_rejected(value):
    with pytest.raises(ValueError):
        server.byte_range(value, 10)


def test_http_range_head_and_file_boundaries(tmp_path):
    payload = b'synthetic-video'
    (tmp_path/'clip.mp4').write_bytes(payload)
    (tmp_path/'captions.vtt').write_text('WEBVTT\n')
    (tmp_path/'secret.txt').write_text('private sentinel')
    (tmp_path/'linked.json').symlink_to(tmp_path/'secret.txt')
    http = ThreadingHTTPServer(('127.0.0.1', 0), partial(server.ReviewHandler, directory=str(tmp_path)))
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{http.server_port}'
    try:
        with urlopen(Request(base+'/clip.mp4', headers={'Range': 'bytes=2-6'}), timeout=5) as response:
            assert response.status == 206 and response.read() == payload[2:7]
            assert response.headers['Content-Range'] == f'bytes 2-6/{len(payload)}'
        with urlopen(Request(base+'/clip.mp4', method='HEAD', headers={'Range': 'bytes=-4'}), timeout=5) as response:
            assert response.status == 206 and response.read() == b''
            assert response.headers['Content-Length'] == '4'
        with urlopen(Request(base+'/clip.mp4', headers={'Range': 'bytes=2-6', 'If-Range': 'unverified'}), timeout=5) as response:
            assert response.status == 200 and response.read() == payload
        with urlopen(base+'/captions.vtt', timeout=5) as response:
            assert response.headers['Content-Type'] == 'text/vtt; charset=utf-8'
        for name, code, headers in [('clip.mp4', 416, {'Range': 'bytes=999-'}),
                                    ('secret.txt', 404, {}), ('linked.json', 404, {}),
                                    ('%2e%2e%2foutside.json', 404, {})]:
            with pytest.raises(HTTPError) as error:
                urlopen(Request(base+'/'+name, headers=headers), timeout=5)
            assert error.value.code == code
            error.value.close()
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)
