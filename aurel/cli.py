import argparse
import json
from pathlib import Path
import platform
import numpy as np
from .core import ToyModel, synthetic_cases, transform, expected_label
from .search import search, solve_game


def main():
    p = argparse.ArgumentParser(description='Synthetic AuRel pipeline smoke experiment')
    p.add_argument('--output', type=Path, default=Path('runs/demo'))
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--budget', type=int, default=80)
    args = p.parse_args()
    if args.budget < 1:
        p.error('--budget must be positive')
    cases = list(synthetic_cases(40, args.seed))
    train = [c for c in cases if int(c.group) < 20]
    test = [c for c in cases if int(c.group) >= 20]
    arms = ['identity', 'gain', 'noise', 'reverse']
    defenders = {'raw': ToyModel(), 'normalize': ToyModel(normalize=True)}
    records, searches, matrix = [], {}, []
    for policy in ('random', 'ucb'):
        def evaluate(arm, t):
            case = train[t % len(train)]
            x = transform(case.audio, arm, np.random.default_rng(args.seed+t))
            return defenders['raw'].predict(x, case.sample_rate, case.prompt) != expected_label(case, arm)
        best, history = search(arms, evaluate, args.budget, args.seed, policy)
        searches[policy] = {'best_arm_train': best, 'history': history}
    for arm in arms:
        losses = []
        for name, model in defenders.items():
            rows = []
            for i, case in enumerate(test):
                clean = model.predict(case.audio, case.sample_rate, case.prompt)
                x = transform(case.audio, arm, np.random.default_rng(args.seed+i))
                pred = model.predict(x, case.sample_rate, case.prompt)
                row = {'id': case.id, 'group': case.group, 'task': case.task,
                       'arm': arm, 'defender': name, 'clean_correct': clean == case.label,
                       'expected': expected_label(case, arm), 'prediction': pred,
                       'violation': pred != expected_label(case, arm)}
                rows.append(row)
                records.append(row)
            eligible = [r for r in rows if r['clean_correct']]
            losses.append(sum(r['violation'] for r in eligible)/len(eligible) if eligible else None)
        matrix.append(losses)
    for result in searches.values():
        result['heldout_raw_loss'] = matrix[arms.index(result['best_arm_train'])][0]
    report = {'synthetic_only': True, 'seed': args.seed, 'budget_per_search': args.budget,
              'python': platform.python_version(), 'numpy': np.__version__,
              'train_groups': 20, 'test_groups': 20, 'arms': arms,
              'defenders': list(defenders), 'payoff_matrix': matrix,
              'game': solve_game(matrix), 'searches': searches,
              'note': 'Game fitted on test matrix is descriptive only; evaluate any selected defense on a new split.',
              'query_counts': {'search': 2*args.budget, 'matrix_clean': len(records), 'matrix_transformed': len(records)}}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (args.output/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records), encoding='utf-8')
    print(json.dumps({'synthetic_only': True, 'report': str(args.output/'report.json'), 'payoff_matrix': matrix}))


if __name__ == '__main__':
    main()
