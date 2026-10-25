"""
RUN POLICIES AND SENSITIVITY TEST
"""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from generate_data import ROOT, configuration, load
from optimize import solve


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    cfg = configuration()
    data = load()
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)

    results = [solve(data, scenario, cfg) for scenario in ('S1', 'S2', 'S3')]
    summary = [{key: result[key] for key in
                ('scenario', 'cost_cu', 'recovered_count', 'reworked_seats', 'candidate_count')}
               for result in results]
    write_csv(out / 'summary.csv', summary)
    write_csv(out / 'S3_assignments.csv', results[-1]['selected'])

    fig, ax = plt.subplots(figsize=(6, 3))
    bar = ax.bar([r['scenario'] for r in summary], [r['cost_cu'] for r in summary],
                 color=["#1c682c", "#1C3450", '#1C3450'])
    ax.set_ylabel('Manufacturing cost unit')
    ax.set_title(f'Minimum cost for {cfg["production_demand"]} geometric feasible')
    for rect, row in zip(bar, summary):
        ax.text(rect.get_x() + rect.get_width()/2, rect.get_height()+9,
                f"{row['cost_cu']:.0f} CU\n{row['recovered_count']} recovered",
                ha='center', fontsize=9)
    ax.set_ylim(0, max(r['cost_cu'] for r in summary)*1.20)
    fig.tight_layout()
    fig.savefig(out / 'cost_comparison.png', dpi=300)
    plt.close(fig)


    sensitivity = []
    for surcharge in (0, 10, 20, 30, 40):
        r = solve(data, 'S3', cfg, recovery_surcharge=surcharge)
        sensitivity.append({'recovery_surcharge_cu': surcharge,
                            'cost_cu': r['cost_cu'],
                            'recovered_count': r['recovered_count'],
                            'reworked_seats': r['reworked_seats']})
    write_csv(out / 'recovery_sensitivity.csv', sensitivity)
    fig, ax1 = plt.subplots(figsize=(6, 3))
    x = [r['recovery_surcharge_cu'] for r in sensitivity]
    ax1.plot(x, [r['cost_cu'] for r in sensitivity], 'o-', color='#276a78', label='Total cost')
    ax1.set_xlabel('Additional cost per recovered part')
    ax1.set_ylabel('Minimum production cost', color="#1d515c")
    ax2 = ax1.twinx()
    ax2.plot(x, [r['recovered_count'] for r in sensitivity], 's--', color='#915d2d',
             label='Recovered components')
    ax2.set_ylabel('Recovered components used', color="#915d2d")
    ax2.set_ylim(0, cfg['production_demand']*3+2)
    ax1.set_title('Sensitivity analysis for recovered-component preparation cost')
    fig.tight_layout()
    fig.savefig(out / 'recovery_sensitivity.png', dpi=300)
    plt.close(fig)

    for row in summary:
        print(f"{row['scenario']}: {row['cost_cu']:.2f} CU, "
              f"{row['recovered_count']} recovered, {row['reworked_seats']} reworked seats")


if __name__ == '__main__':
    main()
