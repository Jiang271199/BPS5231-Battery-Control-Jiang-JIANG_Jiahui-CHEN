# KPI master table

Periodic SOC boundary. Cost and carbon count imports only. Peak = maximum hourly-average import (kW). Percentages are changes relative to S1 in the same period. LP rows are relaxation bounds, not controllers. The Pareto flag compares only the reported S0–S5 rule solutions in that period; it does not include oracle MPC or the LP relaxation.

## Full Year

| Strategy | Cost | Δ cost | Carbon (kgCO2) | Δ carbon | Peak (kW) | Δ peak | Mean monthly peak (kW) | Export (kWh) | EFC | Rule Pareto |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| S0 no battery | 1,540.9 | +47.4% | 791.5 | +37.9% | 4.939 | +0.0% | 3.421 | 2,218 | 0 | No |
| S1 PV priority | 1,045.4 | +0.0% | 573.9 | +0.0% | 4.939 | +0.0% | 3.194 | 659 | 224 | Yes |
| S2 peak shaving | 1,102.3 | +5.4% | 600.4 | +4.6% | 4.152 | -15.9% | 2.943 | 861 | 195 | Yes |
| S3 price response | 1,071.0 | +2.4% | 679.9 | +18.5% | 4.939 | +0.0% | 4.534 | 1,429 | 207 | No |
| S4 carbon response | 1,231.3 | +17.8% | 647.0 | +12.7% | 4.939 | +0.0% | 3.414 | 1,344 | 127 | No |
| S5 min_cost = min_carbon | 1,100.4 | +5.3% | 607.5 | +5.8% | 4.624 | -6.4% | 3.024 | 985 | 177 | Yes |
| S5 min_peak | 1,249.8 | +19.5% | 693.9 | +20.9% | 2.799 | -43.3% | 2.799 | 1,565 | 109 | Yes |
| S5 balanced | 1,128.3 | +7.9% | 618.2 | +7.7% | 4.152 | -15.9% | 2.954 | 1,055 | 167 | No |
| S6 MPC perfect cost-only | 905.0 | -13.4% | 588.5 | +2.5% | 7.313 | +48.1% | 5.202 | 709 | 294 |  |
| S6 MPC perfect cost+peak | 929.7 | -11.1% | 599.1 | +4.4% | 2.742 | -44.5% | 2.041 | 709 | 336 |  |
| S6 MPC perfect balanced | 924.8 | -11.5% | 576.8 | +0.5% | 2.848 | -42.3% | 2.104 | 709 | 325 |  |
| S6 MPC perfect peak-heavy | 966.3 | -7.6% | 590.2 | +2.8% | 2.542 | -48.5% | 1.824 | 709 | 338 |  |
| S6 MPC persistence cost+peak | 1,009.7 | -3.4% | 628.0 | +9.4% | 4.034 | -18.3% | 2.980 | 919 | 300 |  |
| S6 MPC persistence balanced | 1,031.7 | -1.3% | 629.2 | +9.6% | 3.950 | -20.0% | 2.949 | 1,016 | 293 |  |
| LP bound: min cost | 862.6 | -17.5% | 565.8 | -1.4% | 7.313 | +48.1% |  | 697 |  |  |
| LP bound: min carbon | 890.8 | -14.8% | 533.6 | -7.0% | 8.055 | +63.1% |  | 697 |  |  |
| LP bound: min peak | 866.9 | -17.1% | 564.0 | -1.7% | 2.366 | -52.1% |  | 697 |  |  |
| LP bound: min cost, peak<=4.5 | 862.6 | -17.5% | 565.6 | -1.4% | 4.500 | -8.9% |  | 697 |  |  |
| LP bound: min cost, peak<=4.0 | 862.6 | -17.5% | 565.5 | -1.5% | 4.000 | -19.0% |  | 697 |  |  |
| LP bound: min cost, peak<=3.5 | 862.8 | -17.5% | 565.5 | -1.5% | 3.500 | -29.1% |  | 697 |  |  |
| LP bound: min cost, peak<=3.0 | 863.3 | -17.4% | 565.5 | -1.5% | 3.000 | -39.3% |  | 697 |  |  |
| LP bound: min cost, peak<=2.5 | 865.3 | -17.2% | 565.7 | -1.4% | 2.500 | -49.4% |  | 697 |  |  |

## Calibration

| Strategy | Cost | Δ cost | Carbon (kgCO2) | Δ carbon | Peak (kW) | Δ peak | Mean monthly peak (kW) | Export (kWh) | EFC | Rule Pareto |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| S0 no battery | 1,087.0 | +36.9% | 569.1 | +29.4% | 4.939 | +0.0% | 3.501 | 1,148 | 0 | No |
| S1 PV priority | 793.9 | +0.0% | 439.9 | +0.0% | 4.939 | +0.0% | 3.423 | 208 | 134 | Yes |
| S2 peak shaving | 823.0 | +3.7% | 454.9 | +3.4% | 4.152 | -15.9% | 3.126 | 328 | 118 | Yes |
| S3 price response | 790.6 | -0.4% | 501.1 | +13.9% | 4.939 | +0.0% | 4.886 | 655 | 132 | Yes |
| S4 carbon response | 894.1 | +12.6% | 480.6 | +9.2% | 4.939 | +0.0% | 3.490 | 595 | 80 | No |
| S5 min_cost = min_carbon | 819.7 | +3.2% | 457.6 | +4.0% | 4.624 | -6.4% | 3.227 | 385 | 109 | Yes |
| S5 min_peak | 905.6 | +14.1% | 509.2 | +15.7% | 2.799 | -43.3% | 2.799 | 740 | 69 | Yes |
| S5 balanced | 833.5 | +5.0% | 463.4 | +5.3% | 4.152 | -15.9% | 3.130 | 424 | 104 | No |
| S6 MPC perfect cost-only | 683.3 | -13.9% | 448.5 | +1.9% | 7.313 | +48.1% | 5.801 | 229 | 194 |  |
| S6 MPC perfect cost+peak | 702.1 | -11.6% | 456.9 | +3.9% | 2.742 | -44.5% | 2.298 | 229 | 229 |  |
| S6 MPC perfect balanced | 698.7 | -12.0% | 441.2 | +0.3% | 2.848 | -42.3% | 2.390 | 229 | 219 |  |
| S6 MPC perfect peak-heavy | 733.6 | -7.6% | 451.9 | +2.7% | 2.542 | -48.5% | 1.986 | 229 | 229 |  |
| S6 MPC persistence cost+peak | 750.1 | -5.5% | 472.3 | +7.3% | 4.034 | -18.3% | 3.197 | 338 | 208 |  |
| S6 MPC persistence balanced | 769.2 | -3.1% | 474.1 | +7.8% | 3.950 | -20.0% | 3.164 | 417 | 199 |  |

## Holdout

| Strategy | Cost | Δ cost | Carbon (kgCO2) | Δ carbon | Peak (kW) | Δ peak | Mean monthly peak (kW) | Export (kWh) | EFC | Rule Pareto |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| S0 no battery | 453.7 | +80.5% | 222.3 | +66.1% | 3.840 | +0.0% | 3.262 | 1,070 | 0 | No |
| S1 PV priority | 251.3 | +0.0% | 133.9 | +0.0% | 3.840 | +0.0% | 2.734 | 451 | 89 | Yes |
| S2 peak shaving | 279.1 | +11.1% | 145.4 | +8.6% | 3.109 | -19.0% | 2.578 | 533 | 77 | Yes |
| S3 price response | 280.2 | +11.5% | 178.7 | +33.5% | 4.939 | +28.6% | 3.829 | 775 | 75 | No |
| S4 carbon response | 337.1 | +34.1% | 166.3 | +24.2% | 3.840 | +0.0% | 3.262 | 749 | 47 | No |
| S5 min_cost = min_carbon | 280.5 | +11.6% | 149.8 | +11.9% | 3.648 | -5.0% | 2.618 | 600 | 68 | No |
| S5 min_peak | 343.9 | +36.8% | 184.5 | +37.8% | 2.799 | -27.1% | 2.799 | 825 | 40 | Yes |
| S5 balanced | 294.6 | +17.2% | 154.7 | +15.6% | 3.109 | -19.0% | 2.601 | 631 | 64 | No |
| S6 MPC perfect cost-only | 221.5 | -11.9% | 139.9 | +4.5% | 6.761 | +76.1% | 4.003 | 479 | 100 |  |
| S6 MPC perfect cost+peak | 227.4 | -9.5% | 142.1 | +6.1% | 2.343 | -39.0% | 1.526 | 479 | 108 |  |
| S6 MPC perfect balanced | 225.9 | -10.1% | 135.5 | +1.2% | 2.348 | -38.8% | 1.530 | 479 | 106 |  |
| S6 MPC perfect peak-heavy | 232.5 | -7.5% | 138.2 | +3.2% | 2.050 | -46.6% | 1.501 | 479 | 109 |  |
| S6 MPC persistence cost+peak | 259.5 | +3.2% | 155.6 | +16.2% | 3.648 | -5.0% | 2.547 | 581 | 92 |  |
| S6 MPC persistence balanced | 262.3 | +4.4% | 155.0 | +15.8% | 3.522 | -8.3% | 2.520 | 599 | 94 |  |
