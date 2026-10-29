"""Caption fidelity and scene boundaries must survive without speech tools."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('captions', ROOT/'scripts/build_browser_captions.py')
captions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(captions)


def inputs():
    return [json.loads((ROOT/name).read_bytes()) for name in
            (captions.PLAN, captions.MEDIA, captions.PROOF)]


def render(plan, media, proof):
    raw_plan = json.dumps(plan, ensure_ascii=False).encode()
    proof['narration_plan_sha256'] = hashlib.sha256(raw_plan).hexdigest()
    return captions.render(raw_plan, json.dumps(media).encode(), json.dumps(proof).encode())


def test_every_narration_character_is_preserved_and_cues_stay_in_audio_windows():
    plan, media, proof = inputs()
    vtt, raw = render(plan, media, proof)
    data = json.loads(raw)
    assert vtt.startswith(b'WEBVTT\n')
    assert data['human_listening_review'] is False and data['ready_to_submit'] is False
    for index, (segment, measured) in enumerate(zip(plan['segments'], media['timeline']), 1):
        cues = [cue for cue in data['cues'] if cue['scene'] == index]
        assert ''.join(cue['text'] for cue in cues) == segment['narration']
        assert cues[0]['start_ms'] == round(measured['start'] * 1000)
        assert cues[-1]['end_ms'] == round((measured['start'] + measured['audio_duration']) * 1000)
        assert all(0 < cue['end_ms'] - cue['start_ms'] and len(cue['text']) <= 40 for cue in cues)
        assert all(a['end_ms'] == b['start_ms'] for a, b in zip(cues, cues[1:]))


def test_vtt_escapes_markup_and_splits_long_sentences_without_losing_text():
    plan, media, proof = inputs()
    text = '<b>合成&未知</b>，' + '保留所有文字' * 20 + '。'
    plan['segments'][0]['narration'] = text
    vtt, raw = render(plan, media, proof)
    assert b'<b>' not in vtt and b'&lt;b&gt;' in vtt and b'&amp;' in vtt
    assert ''.join(c['text'] for c in json.loads(raw)['cues'] if c['scene'] == 1) == text


def test_two_line_captions_do_not_leave_closing_punctuation_on_its_own():
    for text in ('合' * 20 + '。', '合' * 20 + '，' + '成' * 18):
        lines = captions.wrapped_lines(text)
        assert ''.join(lines) == text
        assert all(len(line) <= 20 for line in lines)
        assert lines[1][0] not in '，。'


@pytest.mark.parametrize('case', ['overlap', 'past_end', 'nan', 'infinity', 'bool_time',
                                 'start_frame', 'title', 'newline', 'empty', 'non_object',
                                 'wrong_duration', 'not_synthetic', 'false_review_claim'])
def test_invalid_timing_text_or_evidence_is_rejected(case):
    plan, media, proof = inputs()
    if case == 'overlap': media['timeline'][0]['audio_duration'] = 30
    elif case == 'past_end': media['timeline'][-1]['audio_duration'] = 100
    elif case == 'nan': media['timeline'][0]['start'] = float('nan')
    elif case == 'infinity': media['duration'] = float('inf')
    elif case == 'bool_time': media['timeline'][0]['start'] = False
    elif case == 'start_frame': plan['segments'][0]['start_frame'] = 1
    elif case == 'title': media['timeline'][0]['step'] = 'wrong scene'
    elif case == 'newline': plan['segments'][0]['narration'] = '合成\n字幕'
    elif case == 'empty': plan['segments'][0]['narration'] = ' '
    elif case == 'non_object': media['timeline'][0] = []
    elif case == 'wrong_duration': media['duration'] = 208
    elif case == 'not_synthetic': proof['synthetic'] = False
    elif case == 'false_review_claim': proof['human_listening_review'] = True
    with pytest.raises(ValueError):
        render(plan, media, proof)


def test_unbound_narration_cannot_generate_captions():
    raw = [(ROOT/name).read_bytes() for name in (captions.PLAN, captions.MEDIA, captions.PROOF)]
    plan = json.loads(raw[0]); plan['segments'][0]['narration'] = 'changed'
    with pytest.raises(ValueError, match='不一致'):
        captions.render(json.dumps(plan).encode(), *raw[1:])


def test_committed_outputs_are_reproducible():
    result = subprocess.run([sys.executable, str(ROOT/'scripts/build_browser_captions.py'), '--check'],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
