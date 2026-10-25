"""
CREATING DATASETS

"""
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def configuration():
    return json.loads((ROOT / 'config.json').read_text())


def generate(seed=None):
    config = configuration()
    rng = np.random.default_rng(config['seed'] if seed is None else seed)
    data = {'bodies': [], 'seats': [], 'plungers': []}
    costs = {'bodies': (68, 45), 'seats': (47, 30), 'plungers': (54, 37)}
    for kind in data:
        for source, n in [('new', config['new_per_type']), ('recovered', config['recovered_per_type'])]:
            recovered = source == 'recovered'
            for index in range(n):
                row = {
                    'id': f'{kind[0].upper()}-{source[0].upper()}-{index+1:02d}',
                    'source': source,
                    'eligible': not (recovered and index == n-1),
                    'cost_cu': round(max(5, rng.normal(costs[kind][int(recovered)], 2.5 if not recovered else 7)), 2)
                }
                if kind == 'bodies':
                    row.update(
                        pocket_bore=round(rng.normal(8, .0015 if not recovered else .0045), 6),
                        pocket_depth=round(rng.normal(12, .006 if not recovered else .020), 6),
                        u_bore=.0004 if not recovered else .0009,
                        u_depth=.0010 if not recovered else .0025
                    )
                elif kind == 'seats':
                    row.update(
                        outer_d=round(rng.normal(8.013, .0015 if not recovered else .0045), 6),
                        height=round(rng.normal(3, .008 if not recovered else .025), 6),
                        u_outer=.0004 if not recovered else .0009,
                        u_height=.0010 if not recovered else .0025,
                        rework_allowed=recovered and index % 2 == 0 and index != n-1
                    )
                else:
                    row.update(
                        reach=round(rng.normal(9.060, .008 if not recovered else .025), 6),
                        u_reach=.0010 if not recovered else .0025
                    )
                data[kind].append(row)
    return data


def save(data, folder=ROOT / 'data'):
    folder.mkdir(parents=True, exist_ok=True)
    for kind, rows in data.items():
        with (folder / f'{kind}.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def load(folder=ROOT / 'data'):
    data = {}
    for kind in ('bodies', 'seats', 'plungers'):
        with (folder / f'{kind}.csv').open(newline='') as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            for key, value in row.items():
                if key in ('id', 'source'):
                    continue
                elif key in ('eligible', 'rework_allowed'):
                    row[key] = value == 'True'
                else:
                    row[key] = float(value)
        data[kind] = rows
    return data


if __name__ == '__main__':
    save(generate())
    print('Synthetic data Generated!')
