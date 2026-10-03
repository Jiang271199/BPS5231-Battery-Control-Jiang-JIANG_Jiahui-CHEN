# Towards AI-Assisted Multi-Objective Battery Control for Cost, Operational Carbon, and Peak Grid Import in a Residential Building

## Project overview

This project investigates how battery-control decisions affect electricity cost, imported operational carbon, and peak grid import in a grid-connected residential building. The analysis uses a common building, photovoltaic system, battery model, tariff, and grid-carbon signal so that differences in performance can be attributed to the control strategy rather than to changes in the physical system.

The interim study establishes a reproducible data pipeline, a no-battery reference, and a transparent PV-priority controller. The final study will extend the comparison to peak-shaving, price-responsive, carbon-responsive, and multi-objective control. Bayesian optimisation will be used to search the parameter space of the multi-objective controller, while the battery simulation and KPI calculations remain deterministic and physically constrained.

## Repository navigation

- [EDA findings](docs/05_EDA_Findings.md)
- [No-battery baseline findings](docs/06_Baseline_Findings.md)
- [PV-priority battery findings](docs/07_PV_Priority_Findings.md)
- [Interim comparison findings](docs/08_Interim_Comparison_Findings.md)
- [Final-stage AI-assisted method](docs/09_Final_Method.md)
- [EDA notebook](notebooks/01_EDA.ipynb)
- [Baseline and PV-priority notebook](notebooks/02_Baseline_and_PV_Priority.ipynb)

## Research questions

1. How do alternative battery-control strategies change electricity cost, imported operational carbon, and peak grid import under identical boundary conditions?
2. Where do the three objectives align, and where do they conflict?
3. Can simulation-guided Bayesian optimisation identify control settings that provide defensible Pareto compromises among cost, carbon, and peak demand?

## Case study and data

The case study is `Building_5` from the CityLearn Challenge 2022 Phase All dataset. It represents a residential building in Fontana, California. The study uses 8,760 hourly observations and the following source files:

| File | Information used |
|---|---|
| [`Building_5.csv`](data/raw/Building_5.csv) | Building electricity load, PV profile, and source calendar labels |
| [`pricing.csv`](data/raw/pricing.csv) | Hourly electricity price |
| [`carbon_intensity.csv`](data/raw/carbon_intensity.csv) | Hourly grid-carbon intensity |
| [`weather.csv`](data/raw/weather.csv) | Outdoor temperature, humidity, and solar irradiance |
| [`schema.json`](data/raw/schema.json) | PV, battery, and dataset configuration |

The selected system includes a 4.0 kW PV array, a 6.4 kWh battery, and 5.0 kW nominal battery power. Annual building load is 8,807.64 kWh and annual PV generation is 6,067.64 kWh. The source files contain no missing values in the load, PV, price, or carbon variables used in the analysis.

The original data do not provide complete timestamps. Records are therefore aligned by source row order, and calendar dates are not reconstructed. The study treats the building load and PV generation as fixed boundary inputs; envelope design, indoor comfort, and HVAC end uses are outside the available data boundary.

## Model and accounting boundary

For each hourly time step, net grid exchange is calculated from building load, PV generation, and realised AC-side battery exchange. Positive net exchange is grid import and negative net exchange is export. Electricity cost and operational carbon are calculated from imports only because the dataset provides neither an export tariff nor a defensible exported-carbon credit.

The main performance indicators are:

- annual grid import;
- annual grid export;
- electricity cost;
- imported operational carbon;
- peak hourly grid import;
- PV self-consumption;
- self-sufficiency; and
- battery throughput.

All strategies use the same battery parameters and accounting rules. Initial state of charge is identical across scenarios, and candidate final strategies must finish within 0.05 kWh of the initial state of charge. Intentional battery export is prohibited.

## Interim scenarios

Two scenarios have been implemented:

- **S0 — No battery:** the PV system remains active, while battery charge and discharge are fixed at zero.
- **S1 — PV priority:** PV surplus charges the battery, and the battery discharges only against a simultaneous building-load deficit. Grid charging and intentional battery export are not allowed.

The implementation reproduces the relevant CityLearn v1.3.6 storage equations with the local schema parameters. It is a local model reproduction rather than a complete CityLearn engine execution. Physical and accounting checks are applied to hourly energy balance, battery power, state of charge, import and export, and annual reconciliation.

## Interim results

| Indicator | S0 No battery | S1 PV priority | Change |
|---|---:|---:|---:|
| Grid import | 4,957.95 kWh | 3,651.77 kWh | −26.35% |
| Electricity cost | 1,540.88 currency units | 1,045.42 currency units | −32.15% |
| Imported operational carbon | 791.53 kgCO₂ | 573.93 kgCO₂ | −27.49% |
| Peak grid import | 4.939 kW | 4.939 kW | 0.00% |
| PV self-consumption | 63.45% | 89.14% | +25.69 percentage points |
| Self-sufficiency | 43.71% | 58.54% | +14.83 percentage points |

PV-priority control substantially reduces annual imports, cost, and imported operational carbon by shifting surplus solar generation to later load. It does not reduce the annual maximum grid import. The annual peak occurs at source step 4195, when PV generation and battery state of charge are both zero. The controller lowers the daily maximum in 185 of 365 sequential 24-hour groups, but it does not preserve sufficient energy for the largest annual event. This result motivates an explicit peak target and reserve state-of-charge constraint in the final analysis.

The interim results establish a validated reference and one interpretable control strategy. They do not demonstrate globally optimal cost, carbon, or peak performance.

## Planned final analysis

The final comparison will include:

| Scenario | Control principle | Primary purpose |
|---|---|---|
| S2 | Peak target with reserve state of charge | Reduce peak grid import |
| S3 | Low-price charging and high-price discharge | Reduce electricity cost |
| S4 | Low-carbon charging and high-carbon discharge | Reduce imported operational carbon |
| S5 | Parameterised multi-objective control | Identify cost-carbon-peak compromises |

For S5, Bayesian optimisation will propose combinations of price, carbon, net-load, state-of-charge, and charge/discharge parameters. Each proposal will be evaluated by the same deterministic battery simulation. The optimiser will use the resulting cost, carbon, and peak values to select subsequent candidates; it will not alter the battery equations or accounting rules.

Feasible candidates will be evaluated using raw cost, carbon, and peak values. A candidate is Pareto-dominated only if another candidate is no worse in all three objectives and strictly better in at least one. The final study will report minimum-cost, minimum-carbon, and minimum-peak solutions, together with one balanced solution selected by its distance from the normalised ideal point.

Parameters will be selected using the August-to-March portion of the source sequence. April-to-July will remain a chronological hold-out period, and no thresholds will be revised using hold-out results. Full-year replay will be reported only after the parameters have been fixed.

## Repository contents

```text
BPS5231_Steps9_10_Submission_Package/
├── data/
│   ├── raw/                                   # Source-file snapshots
│   └── processed/                             # Audited hourly inputs
├── notebooks/
│   ├── 01_EDA.ipynb
│   └── 02_Baseline_and_PV_Priority.ipynb
├── figures/                                   # Generated figures
├── results/                                   # KPI, diagnostic, and validation outputs
├── prepare_steps_1_to_4.py
├── 05_exploratory_data_analysis.py
├── 06_no_battery_baseline.py
├── 07_pv_priority_battery.py
├── 08_interim_comparative_analysis.py
├── 09_Final_Method.md
├── build_notebooks.py
└── requirements.txt
```

Key documentation: [05 EDA](docs/05_EDA_Findings.md) · [06 Baseline](docs/06_Baseline_Findings.md) · [07 PV Priority](docs/07_PV_Priority_Findings.md) · [08 Interim Comparison](docs/08_Interim_Comparison_Findings.md) · [09 Final Method](docs/09_Final_Method.md)


## Reproducing the interim analysis

Python 3.11 is recommended. From the project directory, install the required packages:

```bash
python -m pip install -r requirements.txt
```

The interim analysis can be reproduced by running the two notebooks in order:

1. [`01_EDA.ipynb`](notebooks/01_EDA.ipynb) — data audit and exploratory data analysis
2. [`02_Baseline_and_PV_Priority.ipynb`](notebooks/02_Baseline_and_PV_Priority.ipynb) — no-battery baseline, PV-priority control, and Interim comparison

Alternatively, run the analysis scripts directly:

Script files:

- [`prepare_steps_1_to_4.py`](prepare_steps_1_to_4.py)
- [`05_exploratory_data_analysis.py`](05_exploratory_data_analysis.py)
- [`06_no_battery_baseline.py`](06_no_battery_baseline.py)
- [`07_pv_priority_battery.py`](07_pv_priority_battery.py)
- [`08_interim_comparative_analysis.py`](08_interim_comparative_analysis.py)
- [`requirements.txt`](requirements.txt)

```bash
python 05_exploratory_data_analysis.py
python 06_no_battery_baseline.py
python 07_pv_priority_battery.py
python 08_interim_comparative_analysis.py
```

To rebuild the processed input data from an original CityLearn 2022 directory, run:

```bash
python prepare_steps_1_to_4.py --source-dir /path/to/CityLearn_2022_Phase_All_Complete
```

The notebooks call the reviewed analysis scripts rather than maintaining separate implementations. Monetary results are reported as `currency units` because the source data do not identify a specific currency.

## Key outputs

- [EDA figures](figures/eda/)
- [Baseline figures](figures/baseline/)
- [PV-priority figures](figures/pv_priority/)
- [Interim-comparison figures](figures/interim_comparison/)
- [EDA results](results/eda/)
- [Baseline results](results/baseline/)
- [PV-priority results](results/pv_priority/)
- [Interim-comparison results](results/interim_comparison/)

## Limitations

This is a deterministic case study of one residential building and one supplied year. The source lacks complete timestamps, usable indoor-comfort variables, and disaggregated HVAC demand. The interim battery model reproduces relevant CityLearn v1.3.6 equations locally but has not been executed as a complete CityLearn environment. The findings should therefore not be generalised to offices, other climates, alternative tariffs, or different battery sizes without additional cases and sensitivity analysis.

## Key sources

- [CityLearn Challenge 2022 data description](https://www.aicrowd.com/challenges/neurips-2022-citylearn-challenge)
- [CityLearn 2022 challenge and version information](https://www.citylearn.net/citylearn_challenge/2022.html)
- [CityLearn data-unit contract](https://www.citylearn.net/guides/data_unit_contract.html)
- [CityLearn v1.3.6 battery implementation](https://github.com/intelligent-environments-lab/CityLearn/blob/v1.3.6/citylearn/energy_model.py)
- [Nweye et al. (2023), CityLearn Challenge paper](https://proceedings.mlr.press/v220/nweye23a/nweye23a.pdf)
