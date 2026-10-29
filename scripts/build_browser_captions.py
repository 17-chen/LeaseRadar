#!/usr/bin/env python3
"""Build review captions from the committed narration and measured scene audio.

Scene boundaries use measured audio times. Sentence timing is proportional to
text length, not speech recognition or a completed listening review.
"""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'docs/submission/FULL_BROWSER_NARRATION_20261028.json'
MEDIA = 'output/video/LeaseRadar_Full_Browser_Review_20261028.media.json'
PROOF = 'output/video/LeaseRadar_Full_Browser_Review_20261028.proof.json'
PREFIX = 'LeaseRadar_Full_Browser_Review_20261028'
CAPTIONS = f'output/video/{PREFIX}.zh-CN.vtt'
TRANSCRIPT = f'output/video/{PREFIX}.captions.json'
KIND = 'edited_full_automated_browser_demo'


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def timestamp(milliseconds):
    seconds, ms = divmod(milliseconds, 1000)
    minutes, second = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f'{hours:02d}:{minute:02d}:{second:02d}.{ms:03d}'


def phrases(text):
    """Keep punctuation and every character; cap each cue at two short lines."""
    parts = re.findall(r'[^。！？；]+[。！？；]?|[。！？；]', text)
    result = []
    for part in parts:
        while len(part) > 39:
            cut = max(part.rfind('，', 12, 39), part.rfind('、', 12, 39)) + 1
            cut = cut if cut > 0 else 39
            result.append(part[:cut])
            part = part[cut:]
        if part:
            result.append(part)
    return result


def wrapped_lines(text):
    # Leave a character of slack so punctuation can stay with the first line.
    if len(text) <= 20:
        return [text]
    cut = (len(text) + 1) // 2
    if text[cut] in '，。！？；、：）”':
        cut += 1 if cut < 20 else -1
    return [text[:cut], text[cut:]]


def render(plan_bytes, media_bytes, proof_bytes):
    plan, media, proof = [json.loads(data) for data in (plan_bytes, media_bytes, proof_bytes)]
    if any(not isinstance(item, dict) for item in (plan, media, proof)):
        raise ValueError('字幕输入须为对象')
    segments, timeline = plan.get('segments'), media.get('timeline')
    decoded = proof.get('decode_check')
    if (plan.get('capture_kind') != KIND or plan.get('synthetic') is not True
            or media.get('capture_kind') != KIND or media.get('fps') != 10
            or media.get('width') != 1280 or media.get('height') != 840
            or not number(media.get('duration')) or not 200 <= media['duration'] <= 220
            or proof.get('capture_kind') != KIND
            or proof.get('synthetic') is not True
            or proof.get('human_listening_review') is not False
            or proof.get('ready_to_submit') is not False
            or not isinstance(decoded, dict) or decoded.get('full_decode') != 'passed'
            or not number(decoded.get('duration'))
            or abs(decoded['duration'] - media['duration']) > 0.001
            or proof.get('narration_plan_sha256') != hashlib.sha256(plan_bytes).hexdigest()
            or not isinstance(proof.get('sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', proof['sha256'])
            or not isinstance(segments, list) or len(segments) != 10
            or not isinstance(timeline, list) or len(timeline) != 10):
        raise ValueError('字幕旁白、时间线或媒体证明不一致')
    scenes, cues = [], []
    previous_end = 0
    for index, (segment, measured) in enumerate(zip(segments, timeline)):
        if not isinstance(segment, dict) or not isinstance(measured, dict):
            raise ValueError('字幕场景无效')
        text, title = segment.get('narration'), segment.get('step')
        start, duration = measured.get('start'), measured.get('audio_duration')
        frame = segment.get('start_frame')
        if (not isinstance(text, str) or not text.strip() or '\n' in text or '\r' in text
                or not isinstance(title, str) or not title or measured.get('step') != title
                or type(frame) is not int or not number(start) or not number(duration)
                or start < 0 or duration <= 0 or abs(frame / 10 - start) > 0.001
                or start < previous_end - 0.001
                or start + duration > media['duration'] + 0.001):
            raise ValueError('字幕文本或场景时间越界/重叠')
        start_ms, end_ms = round(start * 1000), round((start + duration) * 1000)
        chunks = phrases(text)
        if ''.join(chunks) != text:
            raise ValueError('字幕文本未完整保留')
        offset = 0
        for chunk in chunks:
            begin = start_ms + round((end_ms - start_ms) * offset / len(text))
            offset += len(chunk)
            end = start_ms + round((end_ms - start_ms) * offset / len(text))
            if end <= begin:
                raise ValueError('字幕时长不足')
            cues.append({'start_ms': begin, 'end_ms': end, 'text': chunk, 'scene': index + 1})
        scenes.append({'start': start, 'end': start + duration, 'title': title, 'text': text})
        previous_end = start + duration
    vtt = ['WEBVTT', '', 'NOTE 句内时码按字数估算；未经过逐字听审或语音对齐。', '']
    for index, cue in enumerate(cues, 1):
        text = cue['text']
        lines = wrapped_lines(text)
        vtt.extend([str(index), f'{timestamp(cue["start_ms"])} --> {timestamp(cue["end_ms"])}',
                    '\n'.join(html.escape(line, quote=False) for line in lines), ''])
    transcript = {'schema': 1, 'timing_method': 'measured_scenes_proportional_text',
                  'human_listening_review': False, 'ready_to_submit': False,
                  'narration_sha256': hashlib.sha256(plan_bytes).hexdigest(),
                  'media_sha256': hashlib.sha256(media_bytes).hexdigest(),
                  'review_video_sha256': proof['sha256'], 'duration': media['duration'],
                  'scenes': scenes, 'cues': cues}
    return '\n'.join(vtt).encode(), (json.dumps(transcript, ensure_ascii=False, indent=2) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='核对已生成文件，不写入')
    args = parser.parse_args()
    try:
        outputs = render(*[(ROOT / name).read_bytes() for name in (PLAN, MEDIA, PROOF)])
        paths = [ROOT / name for name in (CAPTIONS, TRANSCRIPT)]
        if args.check:
            if any(path.read_bytes() != data for path, data in zip(paths, outputs)):
                raise ValueError('字幕或逐段稿与旁白/媒体不一致')
        else:
            if any(path.exists() for path in paths):
                raise ValueError('拒绝覆盖已有字幕或逐段稿')
            for path, data in zip(paths, outputs):
                with path.open('xb') as target:
                    target.write(data)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'字幕检查失败：{exc}\n')
    print('字幕与十场景逐段稿核对通过；句内时间为估算，真人听审待完成。')


if __name__ == '__main__':
    main()
