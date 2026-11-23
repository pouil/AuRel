"""Select one metadata pair deterministically and optionally verify its WAV files."""
import argparse
import hashlib
import io
import json
import re
import wave
from pathlib import Path
from urllib.request import urlopen

import numpy as np

from .crema_manifest import REVISION


def select_pair(records):
    groups = {}
    seen = set()
    for item in records:
        if item['status'] != 'metadata_eligible':
            continue
        clip = item['clip_id']
        if clip in seen:
            raise ValueError('duplicate eligible clip')
        seen.add(clip)
        match = re.fullmatch(r'(\d{4})_(IEO|IOM|DFA|IWL)_(NEU|HAP)_(HI|MD|LO|XX)', clip)
        if not match or item['source_revision'] != REVISION:
            raise ValueError('unexpected clip or source revision')
        speaker, sentence, code, _ = match.groups()
        emotion = 'neutral' if code == 'NEU' else 'happy'
        key = f'{speaker}_{sentence}'
        if item['pair_id'] != key or item['intended_emotion'] != emotion:
            raise ValueError('pair metadata mismatch')
        groups.setdefault(key, {}).setdefault(emotion, []).append(item)
    complete = sorted(k for k, v in groups.items() if {'neutral', 'happy'} <= v.keys())
    if not complete:
        raise ValueError('no complete metadata pair')
    group = groups[complete[0]]
    return [min(group[e], key=lambda r: r['clip_id']) for e in ('neutral', 'happy')]


def inspect_wav(data):
    if data.startswith(b'version https://git-lfs'):
        raise ValueError('Git LFS pointer is not audio')
    with wave.open(io.BytesIO(data), 'rb') as wav:
        channels, width, rate, frames = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        if channels != 1 or width != 2 or rate <= 0 or frames <= 0:
            raise ValueError('expected nonempty mono PCM16 WAV')
        raw = wav.readframes(frames)
        if len(raw) != frames * channels * width:
            raise ValueError('truncated WAV frames')
    samples = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768
    if not np.any(samples):
        raise ValueError('silent WAV')
    return {'audio_sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'sample_rate': rate, 'channels': channels, 'duration_seconds': frames / rate,
            'peak': float(np.max(np.abs(samples))), 'rms': float(np.sqrt(np.mean(samples ** 2))),
            'technical_checks_passed': True, 'human_review_status': 'pending'}


def download_wav(clip):
    path = f'{REVISION}/AudioWAV/{clip}.wav'
    with urlopen('https://raw.githubusercontent.com/CheyneyComputerScience/CREMA-D/' + path, timeout=30) as response:
        pointer = response.read(4096)
    match = re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\n'
                         rb'oid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n?', pointer)
    if not match:
        raise ValueError('expected pinned Git LFS pointer')
    expected_hash, expected_size = match[1].decode(), int(match[2])
    if not 0 < expected_size <= 10_000_000:
        raise ValueError('unexpected audio size')
    url = 'https://media.githubusercontent.com/media/CheyneyComputerScience/CREMA-D/' + path
    with urlopen(url, timeout=30) as response:
        data = response.read(expected_size + 1)
    if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError('download does not match pinned LFS hash/size')
    return data, url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download', action='store_true', help='Fetch exactly the selected two WAVs')
    args = parser.parse_args()
    payload = args.manifest.read_bytes()
    pair = select_pair([json.loads(line) for line in payload.decode('utf-8').splitlines() if line.strip()])
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'selection_rule': 'lexicographically first complete pair_id, then first clip_id per emotion',
              'manifest_sha256': hashlib.sha256(payload).hexdigest(), 'source_revision': REVISION,
              'scope': 'single development pair; not representative sampling',
              'audio_validity_confirmed': False, 'clips': pair}
    # Save the choice before networking; never replace a failed download with another pair.
    report_path = args.output / 'pair.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.download:
        for item in pair:
            try:
                data, url = download_wav(item['clip_id'])
                item.update(inspect_wav(data))
                item['download_url'] = url
                (args.output / (item['clip_id'] + '.wav')).write_bytes(data)
            except Exception as exc:
                item['download_error'] = str(exc)
                raise
            finally:
                report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report_path)


if __name__ == '__main__':
    main()
