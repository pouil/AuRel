import importlib.util
import unittest

if importlib.util.find_spec("jiwer"):
    from aurel.score_asr import score


@unittest.skipUnless(importlib.util.find_spec("jiwer"), "install .[evaluation]")
class TestASRScore(unittest.TestCase):
    def test_corpus_weighting_and_empty_answer(self):
        rows = [dict(source_id="a", reference="one two three", clean="one two three", perturbed="one two"),
                dict(source_id="b", reference="four", clean="four", perturbed="")]
        result = score(rows)
        self.assertEqual(result["clean"]["wer"], 0)
        self.assertEqual(result["perturbed"]["wer"], .5)  # Not mean((1/3), 1).
        self.assertEqual(result["wer_increase"], .5)
        self.assertEqual(result["perturbed"]["deletions"], 2)

    def test_invalid_pairs(self):
        row = dict(source_id="a", reference="one", clean="one", perturbed="one")
        for rows in ([], [row, row], [{**row, "clean": None}], [{**row, "reference": " "}]):
            with self.assertRaises(ValueError):
                score(rows)

    def test_policy_and_improvement(self):
        row = dict(source_id="a", reference="One  two", clean="one two", perturbed="One two")
        result = score([row])
        self.assertEqual(result["wer_increase"], -.5)
        self.assertEqual(result["perturbed"]["cer"], 0)
