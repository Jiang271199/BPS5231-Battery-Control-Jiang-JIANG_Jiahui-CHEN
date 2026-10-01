# Interim Step 5: Exploratory Data Analysis (EDA)

The analysis uses `Building_5` from the CityLearn Challenge 2022 Phase All dataset, comprising 8,760 consecutive 1-hour timesteps. Data preprocessing, units and case boundaries are documented in [README.md](../README.md). This file describes only the original inputs and the **potential net exchange inferred from load and PV under no-battery conditions**. No battery control, cost scenario or carbon-emissions scenario is simulated here, and no control strategy is claimed to be superior.

## Calculation definitions and reproducible results

Hourly definitions are: `net = load − PV`; `potential import = max(net, 0)`; `potential PV surplus = max(−net, 0)`. Because each timestep is exactly 1 hour, hourly kWh values are numerically equal to the average kW over that hour. The reported peak is therefore an **hourly-average power peak**, not an instantaneous power peak. Here, “potential” refers only to ideal hourly netting and does not represent verified export or actual storage utilization.

| Metric | Result | Interpretation |
|---|---:|---|
| Annual load | 8,807.64 kWh | Building `non_shiftable_load` |
| Annual PV generation | 6,067.64 kWh | Converted using the 4 kW installed PV capacity and source profile |
| Potential grid import | 4,957.95 kWh | `Σmax(load−PV,0)`, hourly no-battery balance |
| Potential PV surplus | 2,217.95 kWh | `Σmax(PV−load,0)`, not yet the amount that can actually be stored |
| Hours with PV surplus | 2,586 h | About 29.5% of the year |
| No-battery hourly-average import peak | 4.939 kW | `max[max(load−PV,0)]` |
| Top 1% import hours | 88 h | 99th-percentile threshold = 2.846 kW; these hours are not independent peak events |
| Price–carbon Pearson correlation | 0.313 | Descriptive same-hour linear correlation; it does not prove any control trade-off |

Energy-balance check: `8,807.643180 − 6,067.641222 = 2,740.001959 kWh`; likewise, `4,957.950570 − 2,217.948611 = 2,740.001959 kWh`. The two calculations agree. Each source hour label from 1 to 24 occurs 365 times. Monthly totals reconcile with hourly totals.

## Figures and research interpretation

1. [Load, PV and net exchange over a continuous 168-hour period](../figures/eda/01_selected_week_load_pv_net.png): PV often covers the load during daytime and produces negative net exchange, while nighttime is dominated by imports. The interval is simply the **first complete 7-day period**, source steps 1–168, and is used only to illustrate the hourly mechanism; it must not be described as a “typical week” for the full year.
2. [Annual hourly load and PV distributions](../figures/eda/02_diurnal_load_pv.png): mean PV output is concentrated in daytime, while load and PV are not fully synchronized. The shaded region is the 10th–90th percentile interval of 365 samples for each source hour, **not** a confidence interval around the mean.
3. [Monthly load, PV and potential surplus](../figures/eda/03_monthly_energy_surplus.png): load is highest in source month 7 (1,109.48 kWh), PV is highest in source month 6 (682.45 kWh), and potential surplus is highest in source month 4 (336.18 kWh). These are descriptive results for one building and one supplied year and must not be generalized as universal seasonal patterns. The source-year sequence runs from August to the following July.
4. [Electricity price and grid carbon intensity over the same 168-hour period](../figures/eda/04_price_carbon_selected_week.png): price consists of a small number of discrete time-of-use levels, while carbon intensity varies continuously by hour. The two signals are not identical. The figure motivates comparison of control objectives but does not demonstrate that cost reduction and carbon reduction must conflict.
5. [Carbon-intensity distribution by tariff level](../figures/eda/05_price_carbon_by_tariff.png): carbon-intensity distributions overlap substantially across the five tariff levels; Pearson `r=0.313` and Spearman `r=0.421`. Correlations are calculated from the annual time series and are affected by temporal autocorrelation and unequal sample counts across tariff levels; no significance or causal interpretation is claimed.
6. [Timing and annual energy of PV surplus](../figures/eda/06_pv_surplus_opportunity.png): surplus occurs mainly during daytime. The annual 2,217.95 kWh represents one **theoretical upper-bound source of energy that storage might capture**; actual stored energy is constrained by capacity, power, SOC, efficiency and control logic and must not be presented as achievable benefit.
7. [No-battery potential import duration curve and peak-hour distribution](../figures/eda/07_import_peaks_before_battery.png): the top 1% of import hours are concentrated around source hour labels 17–19, especially hour 18. This can inform later peak-shaving rule design, but these thresholds are descriptive only. Tuning and evaluating a controller on the same full-year data would create optimistic in-sample bias.

## Minimum figure set recommended for the Interim slides

Prioritize Figures 1, 3, 5 and 7 in the slides. They correspond respectively to supply–demand mismatch, seasonal context, the relationship between price and carbon signals, and peak-shaving opportunity. Figures 2, 4 and 6 can be retained for the appendix or Q&A. Beside each figure, include one sentence labelled as an “Observation” and one sentence describing the “Research implication” so that EDA is not mistaken for battery-control results.

## Data boundaries and later validation

- The source CSV contains only month, hour labels 1–24 and day-type labels, not complete calendar timestamps. The 168-hour figure therefore uses relative day numbers on the x-axis and does not invent calendar dates.
- The case is a residential building in Fontana, California; it must not be described in the title, captions or conclusions as an office building or a Singapore building.
- This step performs only hourly netting of load and PV. It does not include battery actions, export compensation, distribution-network constraints, measured power or control-forecast errors.
- The currency of the electricity-price data is not explicitly identified in the supplied dataset, so it is reported only as `currency/kWh` and is not assumed to be US dollars.
- The next step should first establish a **no-battery baseline** and verify its electricity cost and imported operational carbon before comparing control strategies under the same data and battery boundary.

Reproducible script: [05_exploratory_data_analysis.py](../05_exploratory_data_analysis.py). Summary outputs: [eda_summary.json](../results/eda/eda_summary.json), [monthly_summary.csv](../results/eda/monthly_summary.csv), [hourly_profile.csv](../results/eda/hourly_profile.csv), [price_carbon_by_tariff.csv](../results/eda/price_carbon_by_tariff.csv), [peak_hours_by_hour.csv](../results/eda/peak_hours_by_hour.csv).
