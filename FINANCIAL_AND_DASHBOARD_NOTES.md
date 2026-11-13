# Conditional financial analysis and interactive demonstration

## Accounting boundary

The main paper's `electricity_cost_currency` is the annual cost of imported
electricity. The additional financial experiment compares each battery policy
with S0, which has the *same PV system* and no battery. For an assumed export
credit \(f\), the annual bill is

\[
B=C_{\mathrm{import}}-fE_{\mathrm{export}}, \qquad
S=B_{S0}-B_{\mathrm{policy}}.
\]

For an assumed up-front installed battery price \(K\), annual fixed operation
and maintenance fraction \(m\), AC-throughput wear price \(w\), and annual AC
throughput \(T\), the constant annual net benefit is \(S-wT-mK\). Its scenario
net present value over \(N\) years at discount rate \(r\) is

\[
\mathrm{NPV}=-K+\sum_{y=1}^{N}\frac{S-wT-mK}{(1+r)^y}.
\]

The break-even installed price is the value of \(K\) making NPV zero. The code
reports discounted payback only if cumulative discounted benefits recover
the assumed installed price within the ten-year horizon.

The example uses ten identical repetitions of the supplied building-year,
\(r=5\%\), annual maintenance equal to 1% of installed price, no export credit,
wear cost 0.05 source currency units per AC-throughput kWh and installed price
500 units per kWh of 6.4 kWh capacity (3,200 units). These are **assumptions for
sensitivity analysis**, not verified market prices. The source electricity
price series does not identify a currency. Battery lifetime, replacement,
future tariff changes, taxation, embodied carbon, and resale value are not
estimated. The hourly physical simulator already includes capacity fade; the
wear price is an additional *monetary proxy*, not another physical degradation
process.

At those example inputs, S1 saves 495.46 units of annual grid bills relative
to S0, but the assumed wear charge is 143.25 units/year and NPV is −727.35
units. Its break-even up-front installed price is 2,524.79 units under the
same wear, maintenance and discount assumptions. S2 saves 438.57 units/year
and has an example NPV of −1,024.11 units. These numbers are conditional
calculations and should **not** be described as measured returns or actual
California battery prices. All scenario combinations are in
`results/final/sensitivity/financial_scenario_grid.csv`.

## Dashboard boundary

`index.html` embeds the saved full-year trajectories and can be opened
locally, without a server or network access. Users can set relative priorities
for cost, imported operational carbon and annual peak. The weighted score
ranks only the existing S1–S5 rule outcomes; its per-metric min–max scaling
depends on this finite set. The score is a decision aid, not an additional
Bayesian optimisation result. It does not assert that the highest-ranked rule
is Pareto-optimal among all possible controllers.

The display also offers 24-hour grid-import and SOC traces, net solar, home,
battery and grid values at a selected source step, and S2 reserve what-if
settings at 0%, 25%, 50% and 75%. The 25% setting is the reported S2 policy;
the other settings keep its selected peak target and charging ceiling fixed
and are newly simulated exploratory cases. They are excluded from the
reported-rule ranking. Perfect-forecast MPC is identified as an oracle
benchmark. A calendar date is not reconstructed from the source sequence.

For a Singapore case, the framework would require local hourly load, PV,
purchase tariffs, export arrangements and grid carbon-intensity data. The
Fontana results and conditional investment assumptions cannot be transferred
as quantitative Singapore predictions.
