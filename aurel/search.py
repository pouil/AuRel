import math
import numpy as np


def search(arms, evaluate, budget, seed=0, policy='ucb'):
    """One evaluate call = one charged transformed-model query, including failures."""
    if budget < 1 or not arms or policy not in ('ucb', 'random'):
        raise ValueError('Invalid budget, arms or policy')
    rng = np.random.default_rng(seed)
    counts = np.zeros(len(arms), dtype=int)
    sums = np.zeros(len(arms))
    history = []
    for t in range(budget):
        if policy == 'random':
            i = int(rng.integers(len(arms)))
        elif (counts == 0).any():
            i = int(np.flatnonzero(counts == 0)[0])
        else:
            i = int(np.argmax(sums/counts + np.sqrt(2*math.log(t+1)/counts)))
        reward = float(evaluate(arms[i], t))
        if not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError('Rewards must lie in [0, 1]')
        counts[i] += 1
        sums[i] += reward
        history.append({'query': t+1, 'arm': arms[i], 'reward': reward})
    means = np.divide(sums, counts, out=np.full(len(arms), -np.inf), where=counts > 0)
    return arms[int(np.argmax(means))], history


def solve_game(matrix, rounds=20000):
    """Fictitious play: row attacker maximizes loss, column defender minimizes it.

    Returns empirical mixtures and an explicit best-response duality gap.
    Approximate finite-game solution, not a general Stackelberg equilibrium.
    """
    a = np.asarray(matrix, dtype=float)
    if a.ndim != 2 or 0 in a.shape or not np.isfinite(a).all() or rounds < 1:
        raise ValueError('Expected finite nonempty matrix and positive rounds')
    rows = np.ones(a.shape[0])
    cols = np.ones(a.shape[1])
    for _ in range(rounds):
        i = int(np.argmax(a @ (cols/cols.sum())))
        j = int(np.argmin((rows/rows.sum()) @ a))
        rows[i] += 1
        cols[j] += 1
    p, q = rows/rows.sum(), cols/cols.sum()
    lower, upper = float(np.min(p @ a)), float(np.max(a @ q))
    return {'attacker': p.tolist(), 'defender': q.tolist(),
            'value': float(p @ a @ q), 'lower': lower, 'upper': upper,
            'duality_gap': upper-lower}
