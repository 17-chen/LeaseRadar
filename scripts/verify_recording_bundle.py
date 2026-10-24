#!/usr/bin/env python3
"""Check a LeaseRadar review ZIP before extracting it.

The manifest travels inside the ZIP, so this checks accidental corruption and
unsafe archive entries. It does not authenticate who produced the archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

MAX_FILES = 200
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def safe_name(name):
    return (name and not name.startswith('/') and '\\' not in name
            and ':' not in name.split('/')[0]
            and all(part not in ('', '.', '..') for part in name.split('/')))


def verify(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > MAX_FILES:
            raise ValueError('文件数量无效')
        names = [entry.filename for entry in entries]
        if len(set(names)) != len(names) or any(not safe_name(name) for name in names):
            raise ValueError('存在重复或不安全路径')
        if 'MANIFEST.json' not in names:
            raise ValueError('缺少MANIFEST.json')
        total = 0
        for entry in entries:
            mode = entry.external_attr >> 16
            if (entry.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or entry.flag_bits & 1
                    or entry.file_size > MAX_FILE_BYTES):
                raise ValueError(f'不安全的ZIP条目：{entry.filename}')
            total += entry.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError('压缩包解压后体积超限')
        manifest_entry = archive.getinfo('MANIFEST.json')
        if manifest_entry.file_size > MAX_MANIFEST_BYTES:
            raise ValueError('MANIFEST.json过大')
        manifest = json.loads(archive.read(manifest_entry))
        files = manifest.get('files') if isinstance(manifest, dict) else None
        if (not isinstance(manifest, dict) or manifest.get('schema') != 1
                or manifest.get('mode') not in ('synthetic_demo', 'synthetic_demo_review_bundle')
                or type(manifest.get('ready_to_submit')) is not bool
                or not isinstance(files, dict)
                or set(files) != set(names) - {'MANIFEST.json'}):
            raise ValueError('清单与ZIP条目不一致')
        for name, expected in files.items():
            if (not isinstance(expected, dict) or type(expected.get('bytes')) is not int
                    or expected['bytes'] < 0 or not isinstance(expected.get('sha256'), str)
                    or not SHA256.fullmatch(expected['sha256'])):
                raise ValueError(f'清单字段无效：{name}')
            entry = archive.getinfo(name)
            if entry.file_size != expected['bytes']:
                raise ValueError(f'文件大小不符：{name}')
            digest = hashlib.sha256()
            size = 0
            with archive.open(entry) as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
            if size != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                raise ValueError(f'文件哈希不符：{name}')
        return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        manifest = verify(args.archive)
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        parser.exit(1, f'校验失败：{exc}\n')
    print(f'校验通过：{len(manifest["files"])}个文件；模式={manifest["mode"]}；'
          f'可提交={manifest["ready_to_submit"]}。清单不证明发布者身份。')


if __name__ == '__main__':
    main()
