# Step 7 — PV-priority battery control

## Scope and method

Building_5 is simulated for 8,760 hourly timesteps. The controller charges only from PV surplus and discharges only to meet the building's simultaneous deficit. Grid charging, intentional battery export, export revenue and exported-carbon credit are excluded. The battery model reproduces the relevant `StorageDevice` and `Battery` equations in CityLearn v1.3.6 using the local schema parameters: 6.4 kWh capacity, 5.0 kW nominal power, zero standing-loss coefficient, and capacity-loss coefficient 1e-05. CityLearn's default part-load efficiency and capacity–power curves are used because the schema does not override them.

## Annual results

| KPI | No battery | PV priority | Change |
|---|---:|---:|---:|
| Grid import (kWh) | 4,957.95 | 3,651.77 | 26.35% reduction |
| Grid export (kWh) | 2,217.95 | 659.22 | 70.28% reduction |
| Electricity cost (currency) | 1,540.88 | 1,045.42 | 32.15% reduction |
| Carbon emissions (kgCO2) | 791.53 | 573.93 | 27.49% reduction |
| Peak grid import (kW) | 4.939 | 4.939 | 0.00% reduction |
| PV self-consumption (%) | 63.45 | 89.14 | +25.69 percentage points |
| Self-sufficiency (%) | 43.71 | 58.54 | +14.83 percentage points |

The battery receives 1,558.73 kWh and supplies 1,306.18 kWh on the AC side, with 252.55 kWh conversion loss. AC-side throughput is 2,864.91 kWh (223.8 equivalent full cycles). Capacity declines from 6.4000 to 6.3857 kWh under the schema degradation model. Initial and terminal SOC are 0.0000 and 0.0000 kWh, respectively.

## Interpretation

This strategy directly targets PV self-consumption rather than price, carbon intensity or demand peaks. Therefore, reductions in cost, carbon and peak load are co-benefits rather than optimized outcomes. The absence of an export tariff means the reported cost is gross import cost only. Carbon is likewise assigned only to imported electricity; no credit is awarded for exports. These conventions are identical to Step 6 and make the comparison internally consistent.

## Accuracy checks

All 15 programmed checks pass: record count, missing values, SOC and power constraints, charging/discharging logic, absence of grid charging and battery-induced export, hourly and annual electrical balances, import/export identity, monotonic capacity degradation, and reproduction of the five saved Step 6 primary KPIs. See `validation_checks.csv` for numerical residuals.

## Reproducibility note

The installed environment did not contain the CityLearn Python package, so this is a transparent local reimplementation of the required legacy battery equations, not a claim that the full CityLearn environment was executed. Reference implementation: https://github.com/intelligent-environments-lab/CityLearn/blob/v1.3.6/citylearn/energy_model.py.
