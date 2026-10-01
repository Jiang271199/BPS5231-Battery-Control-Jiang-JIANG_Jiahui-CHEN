# BPS5231 Topic 16A: Interim Research Package

**Updated:** 2026-10-01

This repository contains the Interim research package for the BPS5231 project: case definition, data preparation and audit, exploratory data analysis (EDA), a no-battery baseline, a PV-priority battery controller, Interim comparative analysis, the Final-stage method, and reproducible code.

The Step 7–8 results provide the first battery-control scenario and a mechanism-based interpretation. They must **not** be presented as cost-optimal, carbon-optimal or peak-optimal control.

## 1. Research topic and case

**Title:** *Multi-Objective Battery Control for Electricity Cost, Operational Carbon and Peak Grid Import in a Grid-Interactive Residential Building*

**Case:** `Building_5` from the CityLearn Challenge 2022 Phase All dataset, representing one detached residential building in Fontana, California, USA. The earlier “Office Building” description was inconsistent with the source and has been corrected. The dataset is processed public research data; it was not measured by this group and should not be generalized directly to Singapore office buildings.

Official challenge data description: <https://www.aicrowd.com/challenges/neurips-2022-citylearn-challenge>

### Research questions

1. Under identical building, PV, battery and data conditions, how do different control rules affect electricity import cost, operational carbon and peak grid import?
2. Are there quantifiable trade-offs among these objectives?
3. Can a parameterized multi-objective control strategy produce meaningful Pareto compromises?

### Dataset screening

| Dataset package | Schema timesteps and buildings | Electricity price | Decision |
|---|---|---|---|
| 2021 Complete | 35,040 one-hour steps; 9 buildings | No `pricing.csv`; building pricing is null | Not suitable for the current cost objective |
| 2022 Phase All Complete | 8,760 one-hour steps; 17 buildings | Hourly pricing available | Main dataset |
| 2023 Complete | 2,208 one-hour steps; 6 buildings | Hourly pricing available | Too short for the full-year primary case |

`Building_5` was selected before any control strategy was run based on data completeness, load/PV scale, potential PV surplus, dynamic price and carbon intensity. It has a 4 kW PV system, a 6.4 kWh battery and 5 kW nominal battery power. Annual load is approximately 8,807.64 kWh and annual PV generation approximately 6,067.64 kWh; PV exceeds load during 2,586 hours. These are **dataset-screening statistics**, not battery-control benefits.

## 2. Data

Five required source files are stored under `data/raw/`:

| File | Purpose | Records |
|---|---|---:|
| `Building_5.csv` | Building load, PV profile and source calendar labels | 8,760 |
| `pricing.csv` | Hourly time-of-use electricity price | 8,760 |
| `carbon_intensity.csv` | Hourly grid carbon intensity | 8,760 |
| `weather.csv` | Outdoor temperature, humidity and solar irradiance | 8,760 |
| `schema.json` | File links and PV/battery parameters | Configuration |

[`prepare_steps_1_to_4.py`](prepare_steps_1_to_4.py) aligns the four CSV files by row order and generates [`building_5_hourly_inputs.csv`](data/processed/building_5_hourly_inputs.csv). Source-file hashes, sizes, variable checks and screening statistics are stored in [`data_audit.json`](data/processed/data_audit.json).

PV conversion follows CityLearn's default per-kW convention:

`PV [kWh/step] = nominal_power [kW] × solar_generation [W/kW] / 1000`

The raw `solar_generation` values must not be interpreted directly as kWh. See the CityLearn data-unit contract: <https://www.citylearn.net/guides/data_unit_contract.html>.

Core data checks confirm 8,760 hourly rows, no missing load/PV/price/carbon values, five electricity-price levels (0.21–0.54 currency/kWh), carbon intensity of 0.07038–0.28180 kgCO₂/kWh, and a price–carbon Pearson correlation of `r = 0.3130`. Complete calendar timestamps are unavailable, so source row order and source month/hour labels are retained.

## 3. Fixed case parameters

| Item | Value |
|---|---:|
| Timestep | 3,600 s |
| PV nominal power | 4.0 kW |
| Battery capacity | 6.4 kWh |
| Battery nominal power | 5.0 kW |
| Battery `efficiency` parameter | 0.9 |
| Capacity-loss coefficient | 0.00001 |
| Standing-loss coefficient | 0.0 |

All compared strategies use the same load, PV, electricity price, carbon intensity and battery parameters. Primary accounting assigns cost and operational carbon only to grid imports; exports receive no revenue or carbon credit.

## 4. Interim progress

Step 5 completes the EDA.

Step 6 establishes the PV-retaining no-battery baseline:

- grid import: 4,957.95 kWh;
- electricity cost: 1,540.88 currency units;
- operational carbon: 791.53 kgCO₂;
- peak grid import: 4.939 kW;
- PV self-consumption: 63.45%.

Step 7 implements a PV-priority controller: charge only from simultaneous PV surplus, discharge only against simultaneous load deficit, no grid charging and no intentional battery export. It reduces grid import to 3,651.77 kWh, electricity cost to 1,045.42 currency units and operational carbon to 573.93 kgCO₂, while PV self-consumption rises to 89.14%. The annual peak remains 4.939 kW.

Step 7 is a **local reproduction of the relevant CityLearn v1.3.6 battery equations**, not a full CityLearn-engine execution. All 15 Step 7 validation checks pass.

Step 8 shows that the PV-priority strategy reduces the daily peak in 185 of 365 sequential 24-hour groups, but the annual maximum occurs at source timestep 4195 when both PV and battery SOC are zero. All 16 Step 8 comparison checks pass. See [Step8_Interim_Comparison_Findings.md](docs/08_Interim_Comparison_Findings.md).

Step 9 defines the Final-stage method: peak-shaving, price-responsive and carbon-responsive strategies, followed by three-objective Pareto analysis. See [09_Final_Method.md](docs/09_Final_Method.md).

## 5. Repository structure

```text
topic16a_interim/
├── data/raw/
├── data/processed/
├── notebooks/
│   ├── 01_EDA.ipynb
│   └── 02_Baseline_and_PV_Priority.ipynb
├── results/
├── figures/
├── 05_exploratory_data_analysis.py
├── 06_no_battery_baseline.py
├── 07_pv_priority_battery.py
├── 08_interim_comparative_analysis.py
├── docs/
│   ├── 05_EDA_Findings.md
│   ├── 06_Baseline_Findings.md
│   ├── 07_PV_Priority_Findings.md
│   ├── 08_Interim_Comparison_Findings.md
│   └── 09_Final_Method.md
└── requirements.txt
```

The two notebooks can be run in sequence to rebuild the Interim analysis. The notebooks call the audited scripts rather than maintaining duplicate algorithm implementations.

**Recommended environment:** Python 3.11.

```bash
python -m pip install -r requirements.txt
jupyter notebook
```

Notebook execution order:

1. [`01_EDA.ipynb`](notebooks/01_EDA.ipynb) — data audit and exploratory data analysis
2. [`02_Baseline_and_PV_Priority.ipynb`](notebooks/02_Baseline_and_PV_Priority.ipynb) — no-battery baseline, PV-priority control and Interim comparison

### Reproduction commands

```bash
python prepare_steps_1_to_4.py --source-dir /path/to/CityLearn_2022_Phase_All_Complete
python 05_exploratory_data_analysis.py
python 06_no_battery_baseline.py
python 07_pv_priority_battery.py
python 08_interim_comparative_analysis.py
```
