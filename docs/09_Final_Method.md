# Step 9 — Final-stage method

## 1. Research aim and scope

The Final study will compare battery-control strategies for the same CityLearn 2022 `Building_5` case. The building load, 4 kW PV system, 6.4 kWh battery, 5 kW nominal battery power, tariff, grid-carbon signal and battery model remain fixed. Only the control rule changes. This isolates the effect of control logic within the selected case.

The study will answer three questions:

1. How do PV-priority, peak-shaving, price-responsive and carbon-responsive control change annual import cost, operational carbon and peak grid import relative to the same no-battery baseline?
2. Which objectives conflict, and when do those conflicts occur?
3. Which non-dominated control settings provide defensible compromises among cost, carbon and peak demand?

The analysis is a deterministic, single-building case study. It does not claim statistical generalisation to offices, other climates or other tariff structures.

## 2. Common model and accounting boundary

All strategies use the battery equations already validated in Step 7. The implementation reproduces the relevant CityLearn v1.3.6 storage equations with the local schema parameters, including the default part-load efficiency curve, capacity-dependent power limit and capacity-loss coefficient. The study will not describe this as a full CityLearn engine run unless the complete package is later installed and independently reproduced.

For each hourly step (t):

- (L_t): building electricity load, kWh per hourly step.
- (G_t): PV generation, kWh per hourly step.
- (B_t): realised AC-side battery exchange, where positive means charging and negative means discharging.
- (N_t = L_t - G_t + B_t): net grid exchange.
- (I_t = \max(N_t, 0)): grid import.
- (E_t = \max(-N_t, 0)): grid export.

The primary accounting excludes export revenue and exported-carbon credit because the dataset does not provide an export tariff or a defensible consequential-carbon factor.

The main KPIs are:

- Electricity cost: (C = \sum_t I_t p_t).
- Operational carbon: (M = \sum_t I_t c_t).
- Peak grid import: (P = \max_t(I_t) / 1\,\mathrm{h}).
- PV self-consumption: (SC = (\sum_t G_t - \sum_t E_t)/\sum_t G_t).
- Self-sufficiency: (SS = 1 - \sum_t I_t/\sum_t L_t).
- Battery AC throughput: (T = \sum_t (B_t^+ + B_t^-)), reported as a degradation proxy rather than a monetary degradation cost.

All comparisons will use identical initial SOC. Candidate strategies must finish within 0.05 kWh of the initial SOC. Grid charging will be disabled during the final 24 hours, and the controller will discharge residual energy only against building demand. A candidate that still violates the terminal condition will be excluded rather than credited with stored energy that was never used.

## 3. Scenarios

| ID | Strategy | Information used | Grid charging | Primary purpose |
|---|---|---|---|---|
| S0 | No battery | Load and PV | No | Common baseline |
| S1 | PV priority | Current load and PV | No | Maximise on-site PV use |
| S2 | Peak shaving | Current net load, target peak, calibrated peak-hour window and SOC reserve | Allowed only below a charging threshold | Reduce maximum import |
| S3 | Price response | Current tariff and SOC | Yes at low-price hours | Reduce import cost |
| S4 | Carbon response | Current carbon intensity and SOC | Yes at low-carbon hours | Reduce operational carbon |
| S5 | Multi-objective control | Price, carbon, net-load target and SOC | Parameter dependent | Generate Pareto compromises |

S0 and S1 are already implemented. S2–S5 are Final-stage methods and must not be presented as completed results in the Interim submission.

## 4. Peak-shaving controller (S2)

The peak-shaving rule will use two parameters: an import target (P_{target}) and a reserve SOC fraction (r).

1. PV surplus charges the battery subject to power, efficiency, capacity and degradation constraints.
2. When pre-battery import exceeds (P_{target}), the controller requests enough discharge to reduce import toward (P_{target}).
3. Outside target events, discharge is blocked while SOC is below (r\times capacity). This prevents the myopic depletion observed at source step 4195 in Step 8.
4. Limited grid charging is permitted only when current import is below a charging ceiling and the battery lacks the reserve required for a peak-hour window. The window is defined from the frequency of top-1% import events by source hour in the calibration period, then frozen before hold-out evaluation. Battery export remains prohibited.

The calibration grid will test (P_{target}) between the 90th and 99.5th percentiles of pre-battery import, reserve fractions from 0 to 0.8, and charging ceilings between the 20th and 60th percentiles of pre-battery import. The selected rule minimises peak import on the calibration period, subject to no more than a pre-declared 5% increase in cost or carbon relative to S1. The 5% bound is a study choice and will be reported as such, not as a universal standard.

## 5. Price-responsive controller (S3)

The price strategy uses low and high tariff thresholds:

- Charge from PV surplus at all times.
- Permit grid charging when (p_t \le p_{low}), subject to a maximum charging SOC.
- Discharge only against building demand when (p_t \ge p_{high}).
- Do not intentionally export stored energy.

Because the dataset contains five tariff levels, thresholds will be selected from observed tariff levels rather than arbitrary continuous values. The calibration will test every valid pair with (p_{low} < p_{high}), together with maximum charging SOC fractions from 0.5 to 1.0. The primary objective is annual import cost, while carbon, peak, throughput and PV self-consumption remain reported outcomes.

## 6. Carbon-responsive controller (S4)

The carbon strategy mirrors S3 using grid-carbon intensity:

- Charge when (c_t \le c_{low}).
- Discharge against building demand when (c_t \ge c_{high}).
- Retain PV-surplus charging and prohibit intentional battery export.

Thresholds will come from calibration-period carbon quantiles: the 10th–40th percentiles for (c_{low}) and the 60th–90th percentiles for (c_{high}). The primary objective is imported operational carbon. This strategy may increase grid import because of conversion losses, so energy use, cost and throughput must be shown beside carbon reduction.

Price and carbon controls will remain separate before multi-objective optimisation. The observed Pearson correlation of 0.313 between the two signals indicates partial alignment only; it does not establish either synergy or conflict by itself.

## 7. Multi-objective search and Pareto analysis (S5)

S5 will use a transparent parameter sweep rather than reinforcement learning. At each hour, price, carbon intensity and pre-battery import will first be normalised with calibration-period bounds. A control-priority score will then be calculated as

\[
s_t = w_p z(p_t) + w_c z(c_t) + w_d z(I_t^{pre}),
\]

where non-negative weights sum to one. A high score permits discharge toward the building deficit, while a low score permits grid charging up to the maximum charging SOC. PV-surplus charging retains priority whenever pre-battery exchange is negative, and intentional battery export remains prohibited. Candidate policies therefore combine the score weights and charge/discharge thresholds with the peak target, reserve SOC and maximum charging SOC. A coarse grid will first remove infeasible regions, followed by a reproducible random or Latin-hypercube sample with a fixed seed if the grid becomes too large.

For every feasible candidate (x), the study will minimise the raw objective vector

\[
f(x) = [C(x),\ M(x),\ P(x)].
\]

A candidate (a) dominates (b) only when it is no worse in all three objectives and strictly better in at least one. The non-dominated candidates form the Pareto set. PV self-consumption, self-sufficiency and battery throughput will be displayed as secondary attributes and will not be hidden inside the three primary objectives.

Three representative Pareto solutions will be reported:

- minimum-cost solution;
- minimum-carbon solution;
- minimum-peak solution;

One balanced solution may also be reported. It will be chosen by minimum Euclidean distance to the normalised ideal point after min–max normalisation within the calibration Pareto set. This selection rule will be frozen before hold-out evaluation. A weighted sum will not be used to define the Pareto frontier because it can miss non-convex trade-offs.

## 8. Calibration and evaluation protocol

The usable source-year sequence runs from August to July, but source step 0 is a leading wraparound record labelled July, hour 24. Step 0 will serve only as a warm-up/initialisation record in split-period analysis. Source steps after that record through the end of March will form the calibration period, and April through source step 8759 will remain a chronological hold-out set. Parameter thresholds and the balanced Pareto solution will be chosen only from the calibration period.

After parameters are frozen:

1. Report calibration and hold-out KPIs separately.
2. Replay each frozen controller over the full 8,760-hour sequence only as a secondary annual case result.
3. Do not use the hold-out period to revise thresholds.
4. State that one hold-out block tests temporal transfer within one supplied year, not cross-year generalisation.

This split sacrifices some seasonal balance but prevents direct tuning on the evaluation period. A monthly leave-one-block-out sensitivity analysis will be added if time permits.

## 9. Validation and decision rules

Each strategy must pass the existing physical and accounting checks plus the following tests:

- 8,760 hourly outputs with no missing numeric values.
- SOC and power limits satisfied at every step.
- Hourly and annual electrical balances close within numerical tolerance.
- No simultaneous grid import and export.
- No intentional battery export.
- Terminal SOC difference no greater than 0.05 kWh.
- Monthly totals reconcile to annual totals.
- KPI differences reproduce independent hourly summations.
- Pareto dominance is recalculated from raw cost, carbon and peak values rather than rounded display values.
- Parameter selection uses calibration data only.

The Final report will distinguish three types of statement: model facts from the schema, study assumptions chosen by the group, and simulation results. It will not claim that a strategy is “optimal” outside the tested parameter space or the single selected building.

## 10. Minimum Final outputs

The Final submission should include a common KPI table for S0–S5, annual net-load and SOC plots, a diagnostic plot around the annual peak, cost and carbon attribution plots, and a two-dimensional Pareto plot with the third objective encoded by colour. A supplementary table should list every non-dominated candidate and its parameters. The discussion should explain why the best strategy differs by objective and whether the balanced solution remains credible on the hold-out period.

## Sources used for the model boundary

- CityLearn Challenge 2022 data description: <https://www.aicrowd.com/challenges/neurips-2022-citylearn-challenge>
- CityLearn 2022 challenge page and version information: <https://www.citylearn.net/citylearn_challenge/2022.html>
- CityLearn data-unit contract: <https://www.citylearn.net/guides/data_unit_contract.html>
- CityLearn v1.3.6 battery implementation: <https://github.com/intelligent-environments-lab/CityLearn/blob/v1.3.6/citylearn/energy_model.py>
- Nweye et al. (2023), CityLearn Challenge paper: <https://proceedings.mlr.press/v220/nweye23a/nweye23a.pdf>
