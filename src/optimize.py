"""
MILP MODEL

"""
from itertools import product
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix
from generate_data import configuration

####Return values
def fit(body, seat, plunger, reduction, config, uncertainty_scale=1.0):
    interference = seat['outer_d'] - body['pocket_bore']
    go_through = (plunger['reach'] + seat['height']
                  - reduction - body['pocket_depth'])
    u_interference = uncertainty_scale * (seat['u_outer'] + body['u_bore'])
    u_go_through = uncertainty_scale * (plunger['u_reach'] + seat['u_height']
                                       + body['u_depth']
                                       + (config['rework_error'] if reduction else 0))
    return (interference, go_through, u_interference, u_go_through)
####

def acceptable(fit_values, config):
    interference, go_through, ui, uo = fit_values
    i0, i1 = config['interference']
    o0, o1 = config['closing_go_through']
    return (i0 <= interference-ui and interference+ui <= i1
            and o0 <= go_through-uo and go_through+uo <= o1)
####

def candidates(data, scenario, config, uncertainty_scale=1.0, recovery_surcharge=0.0):
    if scenario not in ('S1', 'S2', 'S3'):
        raise ValueError('scenario must be S1, S2 or S3')
    if uncertainty_scale < 0 or recovery_surcharge < 0:
        raise ValueError('Sensitivity values must be nonnegative')
    allowed = {
        k: [p for p in data[k]
            if p['eligible'] and (scenario != 'S1' or p['source'] == 'new')]
        for k in data
    }   
    out = []
    for body, seat, plunger in product(allowed['bodies'], allowed['seats'], allowed['plungers']):
        options = [(0., 0.)]
        if scenario == 'S3' and seat['rework_allowed']:
            options.extend(zip(config['seat_height_reductions'][1:],
                               config['seat_rework_cost_cu'][1:]))
        for reduction, rework_cost in options:
            geometry = fit(body, seat, plunger, reduction, config, uncertainty_scale)
            if not acceptable(geometry, config):
                continue
            n_recovered = sum(p['source'] == 'recovered' for p in (body, seat, plunger))
            out.append({
                'body': body['id'], 'seat': seat['id'], 'plunger': plunger['id'],
                'seat_reduction': reduction,
                'cost_cu': round(sum(p['cost_cu'] for p in (body, seat, plunger))
                                 + n_recovered * recovery_surcharge + rework_cost, 2),
                'recovered_count': n_recovered,
                'interference': round(geometry[0], 6),
                'closing_go_through': round(geometry[1], 6)
            })
    return out
###

def solve(data, scenario, config=None, uncertainty_scale=1.0, recovery_surcharge=0.0):
    config = configuration() if config is None else config
    options = candidates(data, scenario, config, uncertainty_scale, recovery_surcharge)
    q = int(config['production_demand'])
    if not options:
        raise RuntimeError(f'{scenario}: no feasible component combinations')
    positions = {}
    row = 1
    for family, key in [('bodies', 'body'), ('seats', 'seat'), ('plungers', 'plunger')]:
        for part in data[family]:
            positions[(key, part['id'])] = row
            row += 1
    rework_row = row
    matrix_rows, matrix_cols = [], []
    for j, option in enumerate(options):
        affected = [0, positions[('body', option['body'])],
                    positions[('seat', option['seat'])],
                    positions[('plunger', option['plunger'])]]
        if option['seat_reduction'] > 0:
            affected.append(rework_row)
        for r in affected:
            matrix_rows.append(r)
            matrix_cols.append(j)
    A = coo_matrix((np.ones(len(matrix_rows)), (matrix_rows, matrix_cols)),
                   shape=(row + 1, len(options))).tocsc()
    lower = np.full(row+1, -np.inf)
    upper = np.ones(row+1)
    lower[0] = upper[0] = q
    upper[rework_row] = config['max_reworked_seats']
    result = milp(
        c=np.array([p['cost_cu'] for p in options]),
        integrality=np.ones(len(options), dtype=int),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(A, lower, upper),
        options={'mip_rel_gap': 0.0, 'time_limit': 90}
    )
    if result.status != 0 or result.x is None:
        raise RuntimeError(f'{scenario}: solver did not certify an optimum: {result.message}')
    selected = [option for option, value in zip(options, result.x) if value > .5]
    if len(selected) != q:
        raise AssertionError('Incorrect production quantity')
    for key in ('body', 'seat', 'plunger'):
        if len({p[key] for p in selected}) != q:
            raise AssertionError(f'A {key} was reused across assemblies')
    if sum(p['seat_reduction'] > 0 for p in selected) > config['max_reworked_seats']:
        raise AssertionError('Rework capacity exceeded')
    return {
        'scenario': scenario,
        'cost_cu': round(sum(p['cost_cu'] for p in selected), 2),
        'recovered_count': sum(p['recovered_count'] for p in selected),
        'reworked_seats': sum(p['seat_reduction'] > 0 for p in selected),
        'candidate_count': len(options),
        'selected': sorted(selected, key=lambda x: x['body'])
    }
