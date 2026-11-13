#!/usr/bin/env python3
"""Purchase-price sensitivity with fixed selected controller parameters.

Re-simulates hourly battery operation under modified import prices. This is
separate from the existing feed-in tariff sensitivity (export compensation).
No re-optimisation of S5; baseline controller parameters remain fixed.
"""
from dataclasses import replace
import json
import numpy as np
import pandas as pd
from battery_study import battery, config, controllers, data, metrics, validation

OUT = config.RESULTS / 'sensitivity' / 'purchase_tariff_sensitivity.csv'
STRATEGIES = ('S1 PV priority', 'S2 peak shaving', 'S3 price response',
              'S5 min_peak', 'S5 balanced')


def main():
    inp = data.load_inputs()
    original = inp.price.copy()
    mean_price = float(original.mean())
    cases = {
        'original': original,
        'uniform_plus_20pct': original * 1.20,
        'wider_price_spread_50pct': np.maximum(0.0, mean_price + 1.5 * (original - mean_price)),
    }
    selected = json.loads((config.RESULTS / 'rule_strategies' / 'selected_parameters.json').read_text())
    p2 = selected['S2 peak shaving']
    p3 = selected['S3 price response']
    s5_selected = pd.read_csv(config.RESULTS / 's5_multiobjective' / 'S5_selected_parameters.csv')
    cal_imp = data.calibration_import(inp)
    # Freeze S5's original calibration normalisation bounds for this sensitivity.
    bounds = controllers.s5_bounds(inp, cal_imp)
    rows = []
    for scenario, new_prices in cases.items():
        modified = replace(inp, price=new_prices)
        policies = {
            'S1 PV priority': controllers.s1_pv_priority(modified),
            'S2 peak shaving': controllers.s2_peak_shaving(modified, p2['target_kw'], p2['reserve_fraction'], p2['ceiling_kw'], p2['charge_hours']),
            'S3 price response': controllers.s3_price_response(modified, p3['low'], p3['high'], p3['max_soc'], p3['ceiling_kw']),
        }
        for label in ('min_peak', 'balanced'):
            match = s5_selected[s5_selected['solution'] == label]
            if len(match) != 1:
                raise ValueError(f'Expected one S5 {label} parameter row, found {len(match)}')
            policies[f'S5 {label}'] = controllers.s5_score_policy(modified, match.iloc[0].to_dict(), bounds)
        for name in STRATEGIES:
            x = battery.simulate_periodic(modified, policies[name])
            checks = validation.validate(x, periodic=True)
            if not checks.passed.all():
                raise AssertionError(f'{scenario}, {name}: validation failed')
            k = metrics.kpis(x)
            rows.append({
                'tariff_scenario': scenario, 'strategy': name,
                'mean_purchase_price_currency_per_kwh': float(new_prices.mean()),
                'electricity_cost_currency': k['electricity_cost_currency'],
                'carbon_emissions_kgco2': k['carbon_emissions_kgco2'],
                'peak_grid_import_kw': k['peak_grid_import_kw'],
                'grid_import_kwh': k['grid_import_kwh'],
                'soc_start_kwh': k['soc_start_kwh'], 'soc_end_kwh': k['soc_end_kwh'],
            })
    result = pd.DataFrame(rows)
    baseline = result[result.tariff_scenario == 'original'].set_index('strategy')
    for key in metrics.KEYS:
        result[key + '_change_vs_original_pct'] = [
            100 * (r[key] / baseline.loc[r['strategy'], key] - 1)
            for _, r in result.iterrows()
        ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    print('Saved:', OUT, 'rows:', len(result))
    print(result[['tariff_scenario', 'strategy', 'electricity_cost_currency',
                  'carbon_emissions_kgco2', 'peak_grid_import_kw']].to_string(index=False))


if __name__ == '__main__':
    main()
