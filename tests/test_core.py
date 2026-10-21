import unittest
import numpy as np
from aurel.core import synthetic_cases, transform, expected_label, ToyModel, validate_audio
from aurel.search import search, solve_game


class Tests(unittest.TestCase):
    def test_task_conditioned_reversal(self):
        for c in synthetic_cases(4):
            x = transform(c.audio, 'reverse', np.random.default_rng(0))
            self.assertEqual(ToyModel().predict(x, c.sample_rate, c.prompt), expected_label(c, 'reverse'))
            self.assertEqual(expected_label(c, 'reverse') == c.label, c.task == 'count')

    def test_noise_reproducibility(self):
        c = next(synthetic_cases())
        a = transform(c.audio, 'noise', np.random.default_rng(8))
        b = transform(c.audio, 'noise', np.random.default_rng(8))
        np.testing.assert_array_equal(a, b)
        snr = 10*np.log10(np.mean(c.audio**2)/np.mean((a-c.audio)**2))
        self.assertAlmostEqual(snr, 25, places=3)

    def test_budget_and_learning(self):
        calls = []
        def evaluate(arm, t):
            calls.append(t)
            return arm == 'good'
        best, history = search(['bad', 'good'], evaluate, 100)
        self.assertEqual(best, 'good')
        self.assertEqual(len(calls), 100)
        self.assertGreater(sum(h['arm'] == 'good' for h in history), 70)

    def test_matching_pennies(self):
        result = solve_game([[1, -1], [-1, 1]])
        self.assertLess(result['duality_gap'], 0.04)
        self.assertAlmostEqual(sum(result['attacker']), 1)

    def test_invalid_audio(self):
        for x in ([], [float('nan')], [2], [[0]]):
            with self.assertRaises(ValueError):
                validate_audio(x)


if __name__ == '__main__':
    unittest.main()
