import io
import unittest
import wave

from aurel.crema_manifest import REVISION
from aurel.crema_pair import inspect_wav, select_pair


def record(speaker, emotion, intensity='XX'):
    return {'status': 'metadata_eligible', 'source_revision': REVISION,
            'clip_id': f'{speaker}_IEO_{emotion}_{intensity}', 'pair_id': f'{speaker}_IEO',
            'intended_emotion': 'neutral' if emotion == 'NEU' else 'happy'}


class PairTests(unittest.TestCase):
    def test_selection_stable_and_never_crosses_speakers(self):
        records = [record('1000', 'NEU'), record('1001', 'HAP', 'LO'),
                   record('1001', 'HAP', 'HI'), record('1001', 'NEU')]
        result = select_pair(records)
        self.assertEqual(result, select_pair(list(reversed(records))))
        self.assertEqual([r['clip_id'] for r in result], ['1001_IEO_NEU_XX', '1001_IEO_HAP_HI'])
        with self.assertRaises(ValueError):
            select_pair([record('1000', 'NEU'), record('1001', 'HAP')])

    def test_bad_metadata_rejected(self):
        row = record('1001', 'NEU')
        for broken in [dict(row, source_revision='unknown'), dict(row, pair_id='1002_IEO')]:
            with self.assertRaises(ValueError):
                select_pair([broken, record('1001', 'HAP')])
        with self.assertRaises(ValueError):
            select_pair([row, row, record('1001', 'HAP')])

    def test_wav_checks_and_human_review_remains_pending(self):
        out = io.BytesIO()
        with wave.open(out, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b'\x10\x00' * 160)
        data = out.getvalue()
        result = inspect_wav(data)
        self.assertAlmostEqual(result['duration_seconds'], 0.01)
        self.assertEqual(result['human_review_status'], 'pending')
        for invalid in [data[:-2], data[:44] + b'\x00' * 320,
                        b'version https://git-lfs.github.com/spec/v1\n']:
            with self.subTest(size=len(invalid)), self.assertRaises(ValueError):
                inspect_wav(invalid)
