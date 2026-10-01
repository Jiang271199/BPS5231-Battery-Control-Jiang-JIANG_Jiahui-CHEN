# Interim Step 6: No-Battery Baseline

This step establishes the common comparison baseline for all subsequent battery-control strategies. The case remains `Building_5` from the CityLearn Challenge 2022 Phase All dataset: the 4 kW PV system is retained, battery charging, discharging and throughput are fixed at zero, and deterministic hourly accounting is performed over 8,760 consecutive 1-hour steps.

The CityLearn battery engine is not called in this step. Without a battery, the baseline can be calculated directly and transparently from load and PV; this also prevents unverified assumptions about initial battery SOC, minimum SOC or efficiency implementation from affecting the reference case. Once battery strategies are introduced, the CityLearn version and battery implementation must be fixed, and all KPIs must be recalculated using exactly the same accounting conventions.

## Accounting boundary

Hourly calculations are defined as follows:

- `direct PV use = min(load, PV)`
- `grid exchange = load − PV`
- `grid import = max(grid exchange, 0)`
- `grid export = max(−grid exchange, 0)`
- `cost = grid import × electricity price`
- `operational carbon = grid import × grid carbon intensity`

The primary analysis assigns cost and carbon only to imported electricity. The dataset does not provide an export tariff, so export revenue is set to zero; exported electricity is also given no carbon credit. The price unit is retained as `currency/kWh` and is not assumed to be US dollars. Peak demand is the maximum average import power over a 1-hour timestep, not an instantaneous power peak.

## Annual baseline results

| KPI | No-battery baseline | Use in later comparisons |
|---|---:|---|
| Building load | 8,807.64 kWh | Fixed exogenous demand |
| PV generation | 6,067.64 kWh | Fixed exogenous generation |
| Direct PV use | 3,849.69 kWh | Baseline self-consumption that storage may increase |
| Grid import | 4,957.95 kWh | Purchased-energy baseline for battery strategies |
| Grid export | 2,217.95 kWh | Source of potential surplus capture, but not equal to achievable battery charging |
| Electricity cost | 1,540.88 currency | `Σ(import × price)` |
| Operational carbon | 791.53 kgCO₂ | `Σ(import × carbon intensity)` |
| Hourly-average import peak | 4.939 kW | Peak-shaving baseline |
| PV self-consumption | 63.45% | `direct PV use / PV generation` |
| Self-sufficiency | 43.71% | `direct PV use / load` |
| Grid import share of load | 56.29% | `grid import / load` |
| Battery throughput | 0 kWh | Confirms that the baseline contains no storage action |

Annual energy balance is satisfied:

- `3,849.692611 + 4,957.950570 = 8,807.643180 kWh`, i.e. direct PV use plus imports equals load;
- `3,849.692611 + 2,217.948611 = 6,067.641222 kWh`, i.e. direct PV use plus exports equals PV generation;
- `4,957.950570 − 2,217.948611 = 2,740.001959 kWh`, consistent with `load − PV`.

The highest annual import occurs at source timestep 4,195, source month 1 and source hour label 19, with a value of 4.9388 kW. Because the source files do not contain complete calendar timestamps, this event must not be reported as a specific real-world calendar date.

## Figure interpretation

1. [168-hour no-battery grid exchange](../figures/baseline/01_baseline_selected_period.png): daytime PV surplus produces exports, while nighttime and evening periods rely mainly on grid imports. The selected interval is simply the consecutive source steps 1–168, not a screened “typical week”.
2. [Monthly baseline KPIs](../figures/baseline/02_baseline_monthly_kpis.png): source month 1 has relatively high imports, electricity cost, operational carbon and peak import, while source months 3–5 have higher exports. This indicates that peak shaving, cost reduction and higher PV self-consumption may emphasize different seasons, so strategies should not be evaluated using a single month.
3. [Cumulative electricity cost and operational carbon](../figures/baseline/03_baseline_cumulative_cost_carbon.png): the cumulative curves increase faster during high-import months and reach 1,540.88 currency units and 791.53 kgCO₂ by the end of the year. These annual values are the denominator baselines for later strategy reductions.
4. [Diurnal energy, cost and carbon contributions](../figures/baseline/04_baseline_diurnal_contributions.png): direct PV use and exports occur during daytime, while import and cost contributions rise noticeably in the evening. This supports the design of peak-shaving or price-responsive strategies, but average profiles alone should not be used to determine control thresholds.

## Tariff levels and cost structure

The two highest tariff levels, 0.50 and 0.54 currency/kWh, account for only about 28.8% of annual imported energy but about 48.0% of annual electricity cost. This provides a clear economic motivation for price-responsive control. However, actual savings depend on whether sufficient SOC can be made available before these periods and must account for battery conversion losses.

As a background sensitivity reference, if the same load had no PV while retaining the same electricity price and carbon-intensity series, import cost would be 2,454.61 currency units and operational carbon would be 1,447.60 kgCO₂. Relative to the current PV/no-battery baseline, the differences are 913.73 currency units and 656.06 kgCO₂. This comparison reflects only the accounting difference between “with PV” and “without PV”; it is **not a battery benefit**, and exported electricity is not assigned a value.

## Research boundary and rules for later comparisons

- Every later battery strategy must use the same load, PV, electricity price, carbon intensity and import/export accounting conventions.
- Strategy improvement should be calculated relative to this baseline, e.g. `(baseline cost − strategy cost) / baseline cost`.
- Battery strategies must report initial and terminal SOC, charge/discharge energy and throughput. If terminal SOC differs, cost and carbon results cannot be compared fairly without adjustment.
- If export tariffs or exported-carbon credits are introduced later, they must be reported as separate sensitivity scenarios rather than replacing the primary baseline.
- The no-battery baseline requires no battery-efficiency assumption; once battery strategies begin, the actual efficiency implementation in the selected CityLearn version must be verified.

Reproducible script: [06_no_battery_baseline.py](../06_no_battery_baseline.py). Core outputs include [baseline_summary.json](../results/baseline/baseline_summary.json), [baseline_kpis.csv](../results/baseline/baseline_kpis.csv), [hourly_no_battery_baseline.csv](../results/baseline/hourly_no_battery_baseline.csv), [monthly_no_battery_baseline.csv](../results/baseline/monthly_no_battery_baseline.csv), [hourly_clock_no_battery_baseline.csv](../results/baseline/hourly_clock_no_battery_baseline.csv) and [price_tier_no_battery_baseline.csv](../results/baseline/price_tier_no_battery_baseline.csv).
