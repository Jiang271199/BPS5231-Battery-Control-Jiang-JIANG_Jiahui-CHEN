# Step 8 — Interim comparative analysis

## Result

The PV-priority strategy reduces annual grid import by 26.35%, import-only electricity cost by 32.15%, and operational carbon by 27.49%. PV self-consumption rises by 25.69 percentage points. These effects support the claim that the rule improves on-site PV utilization and reduces grid dependency.

## Peak-load interpretation

The annual peak remains 4.939 kW. It occurs at source time step 4195, month 1, source hour 19. At that hour PV is 0.000 kWh and battery SOC is 0.000 kWh, so the battery cannot discharge. This is a mechanism-based explanation: a myopic PV-priority rule uses stored energy whenever a deficit occurs and does not reserve charge for a future annual peak.

This does not mean that the battery never reduces peaks. Daily peaks are lower on 185 of 365 sequential 24-hour groups, with a mean reduction of 0.437 kW and a maximum reduction of 2.344 kW. However, the single largest annual event is unchanged.

## Scientific interpretation

Cost and carbon savings are consequences of avoided imports at the times when PV-charged energy is discharged. The controller does not observe price or carbon intensity, so savings by price tier or carbon quintile are descriptive attributions, not evidence of cost-optimal or carbon-optimal control. A fair next experiment is a peak-shaving controller with a reserve SOC or forecast-informed target, evaluated using the same battery model and accounting conventions.

## Accuracy and limitations

All 16 Step 8 checks pass, in addition to all 15 inherited Step 7 battery checks. Annual hourly sums reproduce both scenario summaries; monthly totals reconcile; cost and carbon savings match independent differences; no daily peak increases; and initial and terminal SOC are both zero. The 0.000588 kWh difference between annual discharge and avoided import is below 0.001 kWh and arises from the documented CityLearn v1.3.6 capacity-fade clamp artifact.

The results are deterministic for one residential building and one supplied year. They do not establish statistical generalizability or causal effects for offices, other climates, other tariffs, or other battery sizes. Source month/hour labels are retained because full calendar timestamps are unavailable.
