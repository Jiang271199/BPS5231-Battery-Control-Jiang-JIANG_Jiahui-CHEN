# Multi-Objective Battery Control in a Residential Building

Reproducible research code for BPS5231. Case: CityLearn 2022 Challenge (Phase All) `Building_5`.
Load, PV, tariff and grid carbon intensity are fixed; we compare how the **same battery**
(6.4 kWh, 5 kW) should be controlled to trade off **import cost**, **operational (import) carbon**
and **peak grid import**.

| ID | Strategy | How parameters are chosen |
|---|---|---|
| S0 | No battery | – |
| S1 | PV priority (charge from PV surplus, discharge to any deficit) | none |
| S2 | Peak shaving with pre-peak reserve | 12-point grid; min calibration peak s.t. cost and carbon ≤ 1.05 × S1 |
| S3 | Price response (tariff thresholds) | 90-point grid; min calibration cost |
| S4 | Carbon response (carbon-intensity thresholds) | 144-point grid; min calibration carbon |
| S5 | Weighted price/carbon/import score rule, 9 encoded dimensions (8 independent after weight normalisation) | ParEGO (Gaussian-process Bayesian optimisation), 80 evaluations |
| S6 | 24-h rolling-horizon MPC (benchmark) | fixed weights; perfect or day-ahead persistence forecast |
| LP | Annual linear-programme bound | relaxed battery benchmark under the study's accounting boundary; not a directly attainable controller |

S1–S6 energy flows and KPIs come from one hourly simulator that reproduces the CityLearn v1.3.6
`Battery` equations (efficiency and power curves, capacity fade). S0 is calculated directly from
load and PV; LP rows are outputs of a separate relaxed optimisation model. The battery simulator
is a local reproduction, not a full CityLearn environment run. Cost and carbon count imports only;
currency is unspecified in the source data. One building, one supplied year.

## Key design decisions

* **Periodic SOC boundary.** Every simulated window starts with the SOC it ends with (fixed-point
  iteration, tolerance 1e-4 kWh). No strategy gains or loses stored energy at the edges, so no
  end-of-horizon "empty the battery" override is needed. The interim study used such an override
  for the last 24 h, which disabled peak protection on the hold-out's largest-load day and capped
  every strategy's hold-out peak at 3.840 kW.
* **Chronological split.** Calibration = source steps 1–5832 (Aug–Mar), used only for parameter
  selection, simulated on its own with a periodic boundary. Hold-out = steps 5833–8759 (Apr–Jul).
  Reported calibration/hold-out/full-year KPIs are slices of one full-year periodic run.
* **Peak** = maximum hourly-average import (kW). Mean monthly peak, top-10-hour mean and P99 are also
  reported because a single-hour maximum is fragile.

## Layout

```
battery_study/            shared package
  config.py               paths, split, boundary settings
  data.py                 input loading
  battery.py              CityLearn v1.3.6 battery equations, periodic-boundary simulation with convergence check
  controllers.py          S1–S5 rules (S5 parameter decoding)
  metrics.py              KPIs, Pareto mask, exact 3-D hypervolume
  validation.py           11 physical/accounting checks (+ per-strategy rule checks)
  evaluate.py             calibration scoring and full-year reporting
  search.py               ParEGO and random search
  mpc.py                  rolling MPC and annual LP bound
  style.py                figure style (white background, portable fonts, fixed strategy colours)
  registry.py             rebuild selected policies from saved parameters
20_run_rule_strategies.py S0–S4
21_run_s5_search.py       S5 ParEGO search (seed 5231) and selected solutions
22_run_search_benchmark.py ParEGO vs random, 10 seeds × 80 evaluations, hypervolume
23_run_mpc_and_bound.py   S6 MPC variants and LP bounds
24_run_sensitivity.py     boundary-SOC and feed-in-tariff sensitivity
25_build_kpi_master.py    unified KPI table and cross-rule Pareto comparison
26_make_publication_figures.py  Fig01–Fig09 (PNG 300 dpi + PDF)
27_check_common_initial_soc.py  common initial-SOC comparison (supplementary)
28_battery_capacity_efficiency_sensitivity.py  fixed-policy capacity/efficiency scenarios
29_purchase_tariff_sensitivity.py  purchase-price scenarios with fixed parameters
30_financial_scenarios.py  conditional NPV, payback and break-even capital cost
31_build_dashboard.py   rebuilds index.html directly (approved HTML template embedded in script)
index.html               sole generated website; open directly in a browser or publish via GitHub Pages
run_all.py                runs 20–31 then tests
tests/                    regression and invariant tests (pytest)
results/final/            all final outputs; KPI_master_table.{csv,md}
figures/publication/      generated publication figures (supplied as a separate upload)
05–08_*.py               data exploration, S0 baseline and S1 reference
```

## Reproduction

Use Python 3.11.5 with the pinned versions in `requirements.txt`. The orchestration script
limits numerical-library threads to one per worker and the two parallel analyses to two workers.
This controls resource use and keeps the included search benchmark reproducible.

```bash
pip install -r requirements.txt
python run_all.py            # complete final pipeline 20–31 and tests
python run_all.py --interim  # also run interim scripts 05–08 first
```

`tests/test_battery.py` checks that the package simulator reproduces the interim S1 hourly results
(`07_pv_priority_battery.py`) to < 1e-12 kWh, that periodic boundaries close, energy balance holds
for random requests, and that the hypervolume routine is exact on known cases. Figures use Arial if
installed, otherwise Liberation Sans or DejaVu Sans. The search benchmark and MPC each use at most
two worker processes; runtime depends on the local CPU and numerical-library versions.

## Main results (full supplied year, change vs S1)

See `results/final/KPI_master_table.md` and `results/final/Pareto_reported_rules.csv`.

* S1 PV priority already removes 32.2% of S0 cost and 27.5% of S0 carbon; no rule-based strategy beats
  it on cost or carbon.
* Rules buy peak reduction with cost and carbon: S2 −15.9% peak for +5.4% cost / +4.6% carbon;
  S5 min-peak −43.3% peak for +19.5% / +20.9%.
* The solution labelled `S5 balanced` is balanced **within the S5 calibration Pareto set**. It is
  dominated by S2 among the reported rule strategies in calibration, hold-out and full-year comparisons:
  both have the same period peak, but S2 has lower cost and imported carbon. It must not be described
  as a cross-strategy Pareto solution. The cross-rule Pareto table is limited to reported solutions,
  not all 80 S5 candidates.
* With perfect 24-h forecasts, MPC (balanced weights) reaches −11.5% cost, +0.5% carbon and −42.3%
  peak. The relaxed LP lower bound is −17.2% cost at a 2.5 kW peak cap. This number is an optimistic
  benchmark, not evidence that the nonlinear battery simulator can attain it. In this case, the
  perfect-forecast MPC also indicates that much of the rule-based cost–peak trade-off is due to
  short-sighted dispatch. With a naive day-ahead persistence forecast the MPC gain largely disappears.
* ParEGO finds better S5 trade-off sets than equal-budget random search (higher hypervolume in
  10/10 paired seeds, Wilcoxon p = 0.002) **for this building-year, search space, evaluation budget,
  and hypervolume reference point**. This is not evidence of general superiority across buildings.
* Rankings are insensitive to the boundary SOC (0/50/100% or periodic). An export credit ≥ 0.10
  currency/kWh would make S3 cheaper than S1, so the S3 result depends on the import-only accounting.


## Supplementary sensitivity analyses

The following scenarios are additional checks; they do not replace the main S0–S6
controller comparisons or retrain the S5 Gaussian-process search. The original
`24_run_sensitivity.py` produces `boundary_soc_sensitivity.csv`,
`boundary_soc_rank_stability.csv`, and `feed_in_tariff_sensitivity.csv`.

| Script | Experiment | Output under `results/final/sensitivity/` |
|---|---|---|
| `27_check_common_initial_soc.py` | Compare periodic SOC with a common 0 kWh initial SOC | `initial_soc_sensitivity.csv` and `soc_initial_comparison.csv` |
| `28_battery_capacity_efficiency_sensitivity.py` | Fixed-policy capacity and efficiency scenarios | `capacity_efficiency_sensitivity.csv` |
| `29_purchase_tariff_sensitivity.py` | Original tariff, 20% higher tariff, and wider price spread | `purchase_tariff_sensitivity.csv` |
| `30_financial_scenarios.py` | Illustrative capital, wear, export-credit and discounting assumptions | `financial_scenario_grid.csv` and `financial_scenario_example.csv` |

The common-initial-SOC cases do not enforce matching terminal SOC and are
interpreted as sensitivity checks, not fully energy-neutral comparisons.
The capacity/efficiency and purchase-tariff scenarios retain previously selected
controller parameters; they are not new optimisation runs. Export-credit scenarios
recalculate net cost from saved dispatch and do not re-optimise dispatch.

To run only the supplementary scripts after the main results and selected
parameters are available:

```bash
python 27_check_common_initial_soc.py
python 28_battery_capacity_efficiency_sensitivity.py
python 29_purchase_tariff_sensitivity.py
python 30_financial_scenarios.py
python 31_build_dashboard.py
```

## Operating savings versus investment return

The main study reports **annual electricity import cost**. It is not a purchase
decision or a battery investment return. `30_financial_scenarios.py` compares
the battery strategies with S0 (the same PV system without a battery). For a
specified export credit, annual bill saving is the difference in net grid bills.
The script then subtracts a *hypothetical* AC-throughput wear charge and annual
maintenance, applies a 10-year, 5% discounted cash-flow scenario, and reports
NPV, discounted payback within ten years and the break-even installed battery
price. The installed price grid (250, 500, 750 per kWh), wear prices
(0, 0.05, 0.10 per throughput kWh), and 1% annual maintenance are modelling
assumptions, not observed prices. The source tariff has no specified currency.
Repeating one simulated year does not predict future load, tariffs, degradation
or battery replacement. See `FINANCIAL_AND_DASHBOARD_NOTES.md` for equations.

## Interactive control dashboard

`index.html` is the sole standalone, offline page requiring no server or account.
Open it in a modern browser. It shows the saved annual KPIs, a selected 24-hour
schedule, battery SOC, and solar, home, battery and grid net flows. The three
priority sliders rank the **reported S1–S5 rule outcomes** after within-set
min–max scaling; they do not optimise a fresh dispatch. The battery-reserve
slider selects additional S2 what-if simulations with the original target and
charging ceiling fixed. The dashboard labels perfect-forecast MPC as an oracle
benchmark and excludes all MPC cases from the rule ranking. No Singapore
performance is implied: local hourly load, PV, tariffs and carbon signals would
be required before applying the framework there.
