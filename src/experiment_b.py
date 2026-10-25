"""
EXPERIMENT B

"""
import copy
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generate_data import ROOT, configuration, load
from optimize import solve


def stress_inventory(data):
    revised = copy.deepcopy(data)
    # out of tolerance 
    seat = next(s for s in revised['seats'] if s['id'] == 'S-R-01')
    seat['height'] = 3.040
    return revised

def save_csv(path, rows):
    with path.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

def main():
    config = configuration()
    reference = load()
    stressed = stress_inventory(reference)
    a2 = solve(reference, 'S2', config)
    a3 = solve(reference, 'S3', config)
    b2 = solve(stressed, 'S2', config)
    b3 = solve(stressed, 'S3', config)
    output = ROOT / 'results'
    output.mkdir(exist_ok=True)
    rows = [
        dict(experiment=experiment, scenario=scenario,
             cost_cu=result['cost_cu'], recovered=result['recovered_count'],
             reworked_seats=result['reworked_seats'])
        for experiment, scenario, result in
        [('A', 'S2', a2), ('A', 'S3', a3), ('B', 'S2', b2), ('B', 'S3', b3)]
    ]
    save_csv(output / 'experiment_b_comparison.csv', rows)
    save_csv(output / 'experiment_b_s3_assignments.csv', b3['selected'])

    fig, ax = plt.subplots(figsize=(9, 4))
    values = [r['cost_cu'] for r in rows]
    bars = ax.bar(['A / S2', 'A / S3', 'B / S2', 'B / S3'], values)
    for bar, row in zip(bars, rows):
        ax.annotate(f"{row['cost_cu']:.2f} CU\n{row['reworked_seats']} reworked",
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha='center', va='bottom', fontsize=9, xytext=(0, 3),
                    textcoords='offset points')
    ax.set_ylabel('Minimum manufacturing cost')
    ax.set_title('Experiment A vs B')
    ax.set_ylim(0, max(values) * 1.2)
    fig.tight_layout()
    fig.savefig(output / 'experiment_b_comparison.png', dpi=300)
    plt.close(fig)

    for row in rows:
        print(f"{row['experiment']} {row['scenario']}: {row['cost_cu']:.2f} CU, "
              f"{row['recovered']} recovered, {row['reworked_seats']} reworked seats")
    print(f"Experiment B: saves {b2['cost_cu'] - b3['cost_cu']:.2f} CU")
    for chosen in b3['selected']:
        if chosen['seat_reduction']:
            print('Reworked:', chosen)


if __name__ == '__main__':
    main()
