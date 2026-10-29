#!/usr/bin/env python3
"""Serve synthetic video review files on loopback, with single byte ranges."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / 'output/video'


def byte_range(value, size):
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
    if not match or size <= 0 or not any(match.groups()):
        raise ValueError('unsatisfiable range')
    first, last = match.groups()
    if not first:
        suffix = int(last)
        if suffix <= 0:
            raise ValueError('unsatisfiable range')
        return max(0, size - suffix), size - 1
    start, end = int(first), int(last) if last else size - 1
    if start >= size or start > end:
        raise ValueError('unsatisfiable range')
    return start, min(end, size - 1)


class ReviewHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        name = unquote(urlsplit(self.path).path)
        name = 'index.html' if name == '/' else name.removeprefix('/')
        path = Path(self.directory) / name
        if (Path(name).name != name or name in ('.', '..') or path.is_symlink()
                or path.suffix not in ('.html', '.js', '.json', '.vtt', '.mp4', '.webm')
                or not path.is_file()):
            self.send_error(404)
            return None
        try:
            source = path.open('rb')
        except OSError:
            self.send_error(404)
            return None
        size = path.stat().st_size
        start, end = 0, size - 1
        ranged = self.headers.get('Range') and not self.headers.get('If-Range')
        if ranged:
            try:
                start, end = byte_range(self.headers['Range'], size)
            except ValueError:
                source.close()
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return None
        self.send_response(206 if ranged else 200)
        self.send_header('Content-Type', 'text/vtt; charset=utf-8' if path.suffix == '.vtt' else self.guess_type(str(path)))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if ranged:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        source.seek(start)
        self.remaining = end - start + 1
        return source

    def copyfile(self, source, output):
        try:
            while self.remaining > 0:
                chunk = source.read(min(self.remaining, 64 * 1024))
                if not chunk:
                    break
                output.write(chunk)
                self.remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Browsers cancel buffered video requests when seeking.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8017)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('端口须为1024–65535')
    with ThreadingHTTPServer(('127.0.0.1', args.port), partial(ReviewHandler, directory=str(ROOT))) as server:
        print(f'本地合成视频审阅：http://127.0.0.1:{args.port}/；Ctrl-C退出。', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
