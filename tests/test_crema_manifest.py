import csv
import io
import unittest

from aurel.crema_manifest import REVISION, build_manifest


def csv_bytes(fields, rows):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(fields)
    writer.writerows(rows)
    return out.getvalue().encode()


class CremaManifestTests(unittest.TestCase):
    def run_rows(self, rows):
        votes = csv_bytes(['', 'fileName', 'A', 'D', 'F', 'H', 'N', 'S', 'numResponses'], rows)
        mapping = csv_bytes(['Stimulus_Number', 'Filename'], [[1, '1001_IEO_HAP_LO']])
        return build_manifest(votes, mapping, REVISION)

    def test_visual_votes_do_not_rescue_audio(self):
        result = self.run_rows([
            [100001, '1001_IEO_HAP_LO', 0, 0, 0, 3, 6, 0, 9],
            [200001, '1001_IEO_HAP_LO', 0, 0, 0, 9, 0, 0, 9]])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'excluded')
        self.assertAlmostEqual(result[0]['target_vote_fraction'], 1/3)

    def test_threshold_and_pending_audio(self):
        row = self.run_rows([[100001, '1001_IEO_HAP_LO', 0, 0, 0, 6, 4, 0, 10]])[0]
        self.assertEqual(row['status'], 'metadata_eligible')
        self.assertIsNone(row['audio_sha256'])
        self.assertEqual(row['human_review_status'], 'pending')

    def test_zero_votes_and_ties(self):
        for happy, neutral, total, reason in [(0, 0, 0, 'zero_votes'), (5, 5, 10, 'target_not_unique_majority')]:
            with self.subTest(reason=reason):
                row = self.run_rows([[100001, '1001_IEO_HAP_LO', 0, 0, 0, happy, neutral, 0, total]])[0]
                self.assertIn(reason, row['exclusion_reasons'])

    def test_bad_counts_and_modality_fail_closed(self):
        for key, happy, total in [(400001, 6, 10), (100001, -1, 3), (100001, 6, 99), (100001, '6.5', 10)]:
            with self.subTest(key=key, happy=happy, total=total), self.assertRaises(ValueError):
                self.run_rows([[key, '1001_IEO_HAP_LO', 0, 0, 0, happy, 4, 0, total]])

    def test_duplicate_or_mismapped_rows_fail_closed(self):
        row = [100001, '1001_IEO_HAP_LO', 0, 0, 0, 6, 4, 0, 10]
        with self.assertRaises(ValueError):
            self.run_rows([row, row])
        with self.assertRaises(ValueError):
            self.run_rows([[100002, *row[1:]]])

    def test_missing_columns(self):
        with self.assertRaises(ValueError):
            build_manifest(b'bad\n1\n', b'bad\n1\n', REVISION)
