#!/usr/bin/env python3
"""Supplementary SOC-start sensitivity check; does not change the main results."""
import pandas as pd
from battery_study import battery, config, data, metrics, registry, validation


def main():
    inp = data.load_inputs()
    policies = registry.rule_policies(inp)
    rows = []
    for name, policy in policies.items():
        for mode in ('periodic', 'common_start_0'):
            x = (battery.simulate_periodic(inp, policy) if mode == 'periodic'
                 else battery.simulate(inp, policy, initial_soc=0.0))
            checks = validation.validate(x, periodic=(mode == 'periodic'))
            if not checks.passed.all():
                raise AssertionError(f'{name} / {mode}:\n{checks.loc[~checks.passed]}')
            k = metrics.kpis(x, capacity_kwh=float(inp.battery['capacity']))
            rows.append({'strategy': name, 'boundary': mode,
                         'soc_change_kwh': k['soc_end_kwh'] - k['soc_start_kwh'], **k})
    df = pd.DataFrame(rows)
    out = config.RESULTS / 'sensitivity'
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / 'soc_initial_comparison.csv', index=False)
    summary = []
    for name, g in df.groupby('strategy', sort=False):
        p = g.set_index('boundary')
        a, b = p.loc['periodic'], p.loc['common_start_0']
        summary.append({'strategy': name,
                        'periodic_start_kwh': a.soc_start_kwh,
                        'common_start_end_kwh': b.soc_end_kwh,
                        'cost_change_pct': 100*(b.electricity_cost_currency/a.electricity_cost_currency-1),
                        'carbon_change_pct': 100*(b.carbon_emissions_kgco2/a.carbon_emissions_kgco2-1),
                        'peak_change_pct': 100*(b.peak_grid_import_kw/a.peak_grid_import_kw-1)})
    result = pd.DataFrame(summary)
    result.to_csv(out / 'initial_soc_sensitivity.csv', index=False)
    print(result.to_string(index=False, float_format=lambda x: f'{x:.4f}'))
    print('\nImportant: common-start cases are NOT terminal-SOC matched; do not interpret as a fully fair economic comparison.')


if __name__ == '__main__':
    main()
