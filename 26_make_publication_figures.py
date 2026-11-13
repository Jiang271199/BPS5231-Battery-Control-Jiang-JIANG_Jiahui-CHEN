#!/usr/bin/env python3
"""Publication figures (white background, PNG 300 dpi + vector PDF) in figures/publication/."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import FancyBboxPatch
from battery_study import config, data, style
from battery_study.style import COLORS, MARKERS, INK, INK2, MUTED, family

R = config.RESULTS
F = config.FIGURES
style.apply()

SHORT = {
    "S0 no battery": "S0 no battery", "S1 PV priority": "S1 PV priority", "S2 peak shaving": "S2 peak shaving",
    "S3 price response": "S3 price", "S4 carbon response": "S4 carbon",
    "S5 min_cost = min_carbon": "S5 min cost/carbon", "S5 min_peak": "S5 min peak", "S5 balanced": "S5 balanced",
    "S6 MPC perfect cost-only": "MPC-PF cost only", "S6 MPC perfect cost+peak": "MPC-PF cost+peak",
    "S6 MPC perfect balanced": "MPC-PF balanced", "S6 MPC perfect peak-heavy": "MPC-PF peak-heavy",
    "S6 MPC persistence cost+peak": "MPC-DA cost+peak", "S6 MPC persistence balanced": "MPC-DA balanced",
}
HOURLY = {
    "S1 PV priority": R / "rule_strategies/S1_hourly.csv", "S2 peak shaving": R / "rule_strategies/S2_hourly.csv",
    "S3 price response": R / "rule_strategies/S3_hourly.csv", "S4 carbon response": R / "rule_strategies/S4_hourly.csv",
    "S5 balanced": R / "s5_multiobjective/S5_balanced_hourly.csv", "S5 min_peak": R / "s5_multiobjective/S5_min_peak_hourly.csv",
    "S6 MPC perfect balanced": R / "s6_mpc/S6_perfect_balanced_hourly.csv",
    "S6 MPC persistence balanced": R / "s6_mpc/S6_persistence_balanced_hourly.csv",
}
FOOT = dict(fontsize=7, color=MUTED, ha="left", va="top")


def master():
    return pd.read_csv(R / "KPI_master_table.csv")


def fig1_framework():
    fig, ax = plt.subplots(figsize=(style.FULL_WIDTH_IN, 2.9))
    ax.set_axis_off(); ax.set_xlim(0, 100); ax.set_ylim(0, 42)

    def box(x, y, w, h, title, body, edge=INK2, fill="#f6f6f3"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=fill, ec=edge, lw=0.9))
        ax.text(x + 1.2, y + h - 1.6, title, fontsize=8.5, weight="bold", va="top", color=INK)
        ax.text(x + 1.2, y + h - 5.6, body, fontsize=7.1, va="top", color=INK2, linespacing=1.45)

    box(1, 13, 19, 27, "Fixed inputs", "CityLearn 2022\nBuilding_5, 8,760 h\n\nLoad, PV generation\nTariff (5 levels)\nGrid carbon intensity")
    box(24, 13, 28, 27, "Controllers", "S0  no battery\nS1  PV priority\nS2  peak shaving\nS3  price response\nS4  carbon response\nS5  score rule, ParEGO-tuned\nS6  24-h MPC (benchmark)")
    box(56, 13, 24, 27, "Battery simulator", "CityLearn v1.3.6 equations\n6.4 kWh, 5 kW\nefficiency and power\ncurves, capacity fade\nperiodic SOC boundary")
    box(84, 13, 15, 27, "KPIs", "Import cost\nImport carbon\nPeak import\nMonthly peaks\nExport, cycles")
    for x0, x1 in ((20.8, 23.4), (52.8, 55.4), (80.8, 83.4)):
        ax.annotate("", xy=(x1, 26.5), xytext=(x0, 26.5),
                    arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, mutation_scale=9))
    ax.add_patch(FancyBboxPatch((24, 1.5), 34, 7, boxstyle="round,pad=0.3,rounding_size=1", fc="#e3eefc", ec="#2a78d6", lw=0.8))
    ax.text(25.2, 5, "Calibration  Aug–Mar (steps 1–5,832)\nparameter selection only", fontsize=7.3, va="center", color=INK)
    ax.add_patch(FancyBboxPatch((63, 1.5), 36, 7, boxstyle="round,pad=0.3,rounding_size=1", fc="#fbe6dd", ec="#eb6834", lw=0.8))
    ax.text(64.2, 5, "Hold-out  Apr–Jul (steps 5,833–8,759)\nfrozen parameters, never used to select", fontsize=7.3, va="center", color=INK)
    ax.text(1, 5, "Chronological split", fontsize=8, weight="bold", va="center", color=INK)
    style.save(fig, F / "Fig01_framework")


def fig2_inputs(inp):
    d = inp.df.iloc[1:169]; h = np.arange(len(d)) / 24
    fig, axes = plt.subplots(3, 1, figsize=(style.FULL_WIDTH_IN, 4.6), sharex=True,
                             gridspec_kw=dict(height_ratios=[2.2, 1, 1], hspace=0.28))
    a = axes[0]
    a.plot(h, d.load_kwh, color="#3b3a37", label="Building load")
    a.plot(h, d.pv_kwh, color="#eda100", label="PV generation")
    a.plot(h, d.load_kwh - d.pv_kwh, color="#2a78d6", lw=1.2, label="Net load (load − PV)")
    a.axhline(0, color=MUTED, lw=0.8)
    a.set_ylabel("Energy (kWh/h)"); a.set_title("(a) Load, PV and net load")
    a.set_ylim(-2.3, 4.2); a.legend(ncol=3, loc="upper left")
    axes[1].step(h, d.price_per_kwh, where="post", color="#3b3a37")
    axes[1].set_ylabel("Price\n(currency/kWh)"); axes[1].set_title("(b) Electricity tariff")
    axes[2].plot(h, d.carbon_intensity_kg_per_kwh, color="#3b3a37")
    axes[2].set_ylabel("Carbon\n(kgCO$_2$/kWh)"); axes[2].set_title("(c) Grid carbon intensity")
    axes[2].set_xlabel("Day of first full week in the source year (source steps 1–168)")
    axes[2].set_xlim(0, 7); axes[2].set_xticks(range(8))
    style.save(fig, F / "Fig02_inputs_week")


def fig3_heatmap():
    m = master(); m = m.loc[m.period.eq("full_year") & ~m.strategy.str.startswith("LP") & ~m.strategy.eq("S1 PV priority")]
    cols = [("electricity_cost_currency", "Import\ncost"), ("carbon_emissions_kgco2", "Import\ncarbon"),
            ("peak_grid_import_kw", "Annual\npeak"), ("mean_monthly_peak_kw", "Mean\nmonthly peak"),
            ("grid_export_kwh", "Grid\nexport")]
    v = m[[c + "_change_vs_S1_pct" for c, _ in cols]].to_numpy()
    cmap = LinearSegmentedColormap.from_list("div", style.DIVERGING)
    fig, ax = plt.subplots(figsize=(5.45, 4.2))
    ax.grid(False)
    im = ax.imshow(np.clip(v, -60, 60), cmap=cmap, norm=TwoSlopeNorm(0, -60, 60), aspect="auto")
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            val = v[i, j]
            label = f"{val:+.1f}%" if 0 < abs(val) < 1 else f"{val:+.0f}%"
            ax.text(j, i, label if abs(val) < 999 else ">999%", ha="center", va="center", fontsize=7.4,
                    color="white" if abs(val) > 38 else INK)
    ax.set_xticks(range(len(cols)), [c[1] for c in cols]); ax.xaxis.tick_top()
    ax.set_yticks(range(len(m)), [SHORT[s] for s in m.strategy])
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    for y in (0.5, 3.5, 6.5):
        ax.axhline(y + 0.0, color="white", lw=2.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, ticks=[-60, -30, 0, 30, 60])
    cb.set_label("Change vs S1 (%) — blue = lower value", fontsize=7.5); cb.outline.set_visible(False)
    fig.text(0.0, -0.01, "Full supplied year, periodic SOC boundary. Values beyond ±60% are coloured at the limit.\n"
             "S5 balanced is within-search only and is dominated by S2 across the three primary objectives.\n"
             "MPC-PF: perfect forecast; MPC-DA: day-ahead persistence forecast.", **FOOT)
    style.save(fig, F / "Fig03_kpi_heatmap")


def _scatter_points(ax, m, ycol, offsets):
    for _, r in m.iterrows():
        fam = family(r.strategy)
        ax.scatter(r.peak_grid_import_kw, r[ycol], s=46 if fam != "S6" else 80, marker=MARKERS[fam],
                   color=COLORS[fam], edgecolor="white", linewidth=0.8, zorder=3)
        dx, dy, ha = offsets.get(r.strategy, (6, 0, "left"))
        ax.annotate(SHORT[r.strategy], (r.peak_grid_import_kw, r[ycol]), xytext=(dx, dy),
                    textcoords="offset points", fontsize=6.8, color=INK2, ha=ha, va="center")


FIG4_SET = ["S1 PV priority", "S2 peak shaving", "S3 price response", "S4 carbon response",
            "S5 min_cost = min_carbon", "S5 balanced", "S5 min_peak", "S6 MPC perfect cost-only",
            "S6 MPC perfect balanced", "S6 MPC persistence balanced"]


def fig4_tradeoff():
    m = master(); fy = m.loc[m.period.eq("full_year")]
    pts = fy.loc[fy.strategy.isin(FIG4_SET)]
    s0 = fy.loc[fy.strategy.eq("S0 no battery")].iloc[0]
    lp = fy.loc[fy.strategy.str.startswith("LP bound: min cost")].sort_values("peak_grid_import_kw")
    lp_min_peak = fy.loc[fy.strategy.eq("LP bound: min peak")].iloc[0]
    lp_min_carbon = fy.loc[fy.strategy.eq("LP bound: min carbon")].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(style.FULL_WIDTH_IN, 3.9), gridspec_kw=dict(wspace=0.30))
    a = axes[0]
    fx = [lp_min_peak.peak_grid_import_kw] + list(lp.peak_grid_import_kw)
    fyv = [lp_min_peak.electricity_cost_currency] + list(lp.electricity_cost_currency)
    a.plot(fx, fyv, ls="--", color=COLORS["LP"], lw=1.1, zorder=2)
    a.fill_between(fx, 800, fyv, color="#efefec", zorder=1)
    a.text(4.2, fyv[-1] + 8, "LP bound (perfect foresight, relaxed battery)", fontsize=6.6, color=MUTED, va="bottom")
    off_a = {"S1 PV priority": (7, -3, "left"), "S3 price response": (7, 4, "left"),
             "S4 carbon response": (7, 0, "left"), "S2 peak shaving": (-7, -5, "right"),
             "S5 balanced": (-7, 5, "right"), "S5 min_cost = min_carbon": (7, 7, "left"),
             "S5 min_peak": (7, 0, "left"), "S6 MPC perfect cost-only": (0, 10, "center"),
             "S6 MPC perfect balanced": (7, 0, "left"), "S6 MPC persistence balanced": (-7, 0, "right")}
    _scatter_points(a, pts, "electricity_cost_currency", off_a)
    a.set_ylim(840, 1290); a.set_xlim(2.2, 7.8)
    a.set_xlabel("Annual peak grid import (kW)"); a.set_ylabel("Annual import cost (currency units)")
    a.set_title("(a) Cost vs peak")
    b = axes[1]
    b.axhline(lp_min_carbon.carbon_emissions_kgco2, ls="--", color=COLORS["LP"], lw=1.1)
    b.text(7.75, lp_min_carbon.carbon_emissions_kgco2 + 4, "LP carbon bound", fontsize=6.6, color=MUTED, ha="right")
    off_b = dict(off_a)
    off_b.update({"S6 MPC perfect balanced": (0, -11, "left"), "S6 MPC perfect cost-only": (2, 11, "right"),
                  "S5 min_cost = min_carbon": (7, 1, "left"), "S5 balanced": (-7, 4, "right"),
                  "S2 peak shaving": (-7, -4, "right"), "S1 PV priority": (7, 0, "left")})
    _scatter_points(b, pts, "carbon_emissions_kgco2", off_b)
    b.set_ylim(520, 710); b.set_xlim(2.2, 7.8)
    b.set_xlabel("Annual peak grid import (kW)"); b.set_ylabel("Annual import carbon (kgCO$_2$)")
    b.set_title("(b) Carbon vs peak")
    handles = [plt.Line2D([], [], marker=MARKERS[k], color=COLORS[k], ls="", ms=6, label=l)
               for k, l in (("S1", "S1"), ("S2", "S2"), ("S3", "S3"), ("S4", "S4"),
                            ("S5", "S5 (ParEGO-tuned)"), ("S6", "S6 MPC"))]
    handles.append(plt.Line2D([], [], color=COLORS["LP"], ls="--", label="LP bound"))
    fig.legend(handles=handles, ncol=7, loc="upper center", bbox_to_anchor=(0.5, 1.04), handletextpad=0.3, columnspacing=1.0)
    fig.text(0.0, -0.02, f"Full supplied year, periodic SOC boundary; lower-left is better. S0 (no battery, off scale): cost "
             f"{s0.electricity_cost_currency:,.0f}, carbon {s0.carbon_emissions_kgco2:,.0f} kgCO$_2$, peak {s0.peak_grid_import_kw:.2f} kW.\n"
             "S5 balanced is balanced within the S5 search; S2 dominates it on the three annual objectives. "
             "MPC-PF: perfect 24-h forecast; MPC-DA: same-hour-yesterday forecast.", **FOOT)
    style.save(fig, F / "Fig04_tradeoff")


def fig5_diurnal():
    names = ["S1 PV priority", "S2 peak shaving", "S3 price response", "S5 balanced", "S6 MPC perfect balanced"]
    fig, axes = plt.subplots(1, 2, figsize=(style.FULL_WIDTH_IN, 2.9), gridspec_kw=dict(wspace=0.28))
    s0 = data.load_inputs()
    hrs = np.arange(1, 25)
    base = pd.Series(np.clip(s0.net, 0, None)).groupby(s0.hour).mean()
    axes[1].plot(hrs, base.values, color=COLORS["S0"], lw=1.4, label="S0 no battery")
    for n in names:
        x = pd.read_csv(HOURLY[n]); fam = family(n)
        soc = x.groupby("hour").soc_end_kwh.mean(); imp = x.groupby("hour").grid_import_kwh.mean()
        axes[0].plot(hrs, soc.values, color=COLORS[fam], label=SHORT[n])
        axes[1].plot(hrs, imp.values, color=COLORS[fam], label=SHORT[n])
    axes[0].set_ylabel("Mean end-of-hour SOC (kWh)"); axes[0].set_title("(a) State of charge")
    axes[0].set_ylim(0, 6.4)
    axes[1].set_ylabel("Mean grid import (kWh/h)"); axes[1].set_title("(b) Grid import")
    for a in axes:
        a.set_xlabel("Hour of day (source hour 1–24)"); a.set_xticks([1, 6, 12, 18, 24]); a.set_xlim(1, 24)
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, ncol=6, loc="upper center", bbox_to_anchor=(0.5, 1.07))
    fig.text(0.0, -0.03, "Annual means over the full year, periodic SOC boundary.", **FOOT)
    style.save(fig, F / "Fig05_diurnal_operation")


def fig6_peak_event():
    s1 = pd.read_csv(HOURLY["S1 PV priority"]); pk = int(s1.grid_import_kwh.idxmax())
    win = slice(pk - 30, pk + 31); rel = np.arange(-30, 31)
    names = ["S1 PV priority", "S2 peak shaving", "S5 min_peak", "S6 MPC perfect balanced"]
    fig, axes = plt.subplots(2, 1, figsize=(style.FULL_WIDTH_IN, 3.9), sharex=True,
                             gridspec_kw=dict(height_ratios=[1.6, 1], hspace=0.22))
    for n in names:
        x = pd.read_csv(HOURLY[n]).iloc[win]; fam = family(n)
        axes[0].plot(rel, x.grid_import_kwh, color=COLORS[fam], label=SHORT[n], lw=1.8 if fam == "S1" else 1.4)
        axes[1].plot(rel, x.soc_end_kwh, color=COLORS[fam], label=SHORT[n])
    axes[0].axvline(0, color=MUTED, lw=0.8, ls=":")
    axes[0].set_ylabel("Grid import (kWh/h)"); axes[0].set_title("(a) Grid import around the S1 annual peak")
    axes[1].set_ylabel("SOC (kWh)"); axes[1].set_title("(b) Battery state of charge"); axes[1].set_ylim(0, 6.6)
    axes[1].set_xlabel(f"Hours relative to the S1 annual peak (source step {pk}, month {int(s1.month[pk])}, hour {int(s1.hour[pk])})")
    axes[0].set_ylim(0, 6.3); axes[0].legend(ncol=4, loc="upper left")
    style.save(fig, F / "Fig06_peak_event")


def fig7_transfer():
    m = master(); m = m.loc[~m.strategy.str.startswith("LP") & ~m.strategy.isin(["S0 no battery", "S1 PV priority"])]
    order = [s for s in SHORT if s in set(m.strategy) and s not in ("S0 no battery", "S1 PV priority")]
    kp = [("electricity_cost_currency", "Import cost"), ("carbon_emissions_kgco2", "Import carbon"), ("peak_grid_import_kw", "Period peak")]
    fig, axes = plt.subplots(1, 3, figsize=(style.FULL_WIDTH_IN, 3.7), sharey=True, gridspec_kw=dict(wspace=0.08))
    y = np.arange(len(order))[::-1]
    for a, (c, t) in zip(axes, kp):
        for yi, s in zip(y, order):
            g = m.loc[m.strategy.eq(s)].set_index("period")[c + "_change_vs_S1_pct"]
            a.plot([g.calibration, g.holdout], [yi, yi], color="#c9c8c2", lw=1.6, zorder=1)
            a.scatter(g.calibration, yi, s=26, facecolor="white", edgecolor="#2a78d6", lw=1.3, zorder=2)
            a.scatter(g.holdout, yi, s=26, color="#eb6834", zorder=3)
        a.axvline(0, color=INK2, lw=0.8)
        a.set_title(t); a.set_xlabel("Change vs S1 (%)")
        a.grid(axis="y", visible=False)
    axes[0].set_yticks(y, [SHORT[s] for s in order])
    axes[2].set_xlim(-60, 85)
    h = [plt.Line2D([], [], marker="o", ls="", mfc="white", mec="#2a78d6", label="Calibration (Aug–Mar)"),
         plt.Line2D([], [], marker="o", ls="", color="#eb6834", label="Hold-out (Apr–Jul)")]
    fig.legend(handles=h, ncol=2, loc="upper center", bbox_to_anchor=(0.55, 1.05))
    fig.text(0.0, -0.02, "Each strategy is compared with S1 over the same period. Negative = better than S1. "
             "S5 parameters were selected on calibration data only; S6 is not calibrated.", **FOOT)
    style.save(fig, F / "Fig07_calibration_vs_holdout")


def fig8_benchmark():
    c = pd.read_csv(R / "s5_multiobjective/benchmark_hypervolume_curves.csv")
    fig, axes = plt.subplots(1, 2, figsize=(style.FULL_WIDTH_IN, 2.9), gridspec_kw=dict(width_ratios=[1.7, 1], wspace=0.3))
    a = axes[0]
    for meth, col, lab in (("random", "#8a8984", "Random search"), ("parego", COLORS["S5"], "ParEGO (GP-guided)")):
        g = c.loc[c.method.eq(meth)].groupby("evaluations").hypervolume
        q = g.quantile([0.25, 0.5, 0.75]).unstack()
        a.fill_between(q.index, q[0.25], q[0.75], color=col, alpha=0.18, lw=0)
        a.plot(q.index, q[0.5], color=col, label=lab)
    a.axvline(20, color=MUTED, ls=":", lw=0.9)
    a.text(20.8, a.get_ylim()[0] if False else 0.004, "shared initial design ends", fontsize=6.6, color=MUTED)
    a.set_xlabel("Evaluations (each = one calibration-window simulation)"); a.set_ylabel("Hypervolume")
    a.set_title("(a) Search progress, median and IQR over 10 seeds"); a.legend(loc="upper left")
    a.set_xlim(1, 80); a.set_ylim(bottom=0)
    b = axes[1]
    fin = c.loc[c.evaluations.eq(80)].pivot(index="seed", columns="method", values="hypervolume")
    for _, r in fin.iterrows():
        b.plot([0, 1], [r.random, r.parego], color="#c9c8c2", lw=1, zorder=1)
    b.scatter(np.zeros(len(fin)), fin.random, color="#8a8984", s=22, zorder=2)
    b.scatter(np.ones(len(fin)), fin.parego, color=COLORS["S5"], s=22, zorder=2)
    b.set_xticks([0, 1], ["Random", "ParEGO"]); b.set_xlim(-0.35, 1.35)
    b.set_ylabel("Hypervolume after 80 evaluations"); b.set_title("(b) Paired by seed")
    s = pd.read_csv(R / "s5_multiobjective/benchmark_summary.csv", index_col=0)
    b.text(1.0, fin.random.min() + 0.002, f"ParEGO higher in {int(s.loc['parego','paired_wins_parego'])}/10\n"
           f"Wilcoxon p = {s.loc['parego','wilcoxon_p_two_sided']:.3f}", ha="center", fontsize=6.8, color=INK2)
    fig.text(0.0, -0.03, "Objectives normalised by S1 calibration cost, carbon and peak; reference point (1.5, 1.5, 1.01).", **FOOT)
    style.save(fig, F / "Fig08_search_benchmark")


def fig9_feed_in():
    t = pd.read_csv(R / "sensitivity/feed_in_tariff_sensitivity.csv")
    runs = {"S0 no battery": "S0 no battery", "S1": "S1 PV priority", "S3": "S3 price response",
            "S5_balanced": "S5 balanced", "S6_perfect_balanced": "S6 MPC perfect balanced",
            "S6_persistence_balanced": "S6 MPC persistence balanced"}
    fig, ax = plt.subplots(figsize=(style.COLUMN_WIDTH_IN * 1.35, 3.0))
    ends = []
    for run, name in runs.items():
        g = t.loc[t.run.eq(run)].sort_values("feed_in_tariff"); fam = family(name)
        ls = "--" if "persistence" in name else "-"
        ax.plot(g.feed_in_tariff, g.net_cost_currency, color=COLORS[fam], ls=ls, marker=MARKERS[fam], ms=4)
        ends.append([g.net_cost_currency.iloc[-1], SHORT[name], COLORS[fam]])
    ends.sort()
    ypos = []
    for y, lab, col in ends:
        y2 = max(y, ypos[-1] + 30) if ypos else y
        ypos.append(y2)
        ax.text(0.218, y2, lab, fontsize=6.6, color=INK2, va="center")
    ax.set_xlim(0, 0.30); ax.set_xticks([0, 0.05, 0.10, 0.21])
    ax.set_xlabel("Feed-in tariff for exports (currency/kWh)"); ax.set_ylabel("Annual net cost (currency units)")
    ax.set_title("Export-credit sensitivity")
    fig.text(0.0, -0.02, "Main study: 0 (imports only). 0.21 = lowest import tariff.", **FOOT)
    style.save(fig, F / "Fig09_feed_in_sensitivity")


def main():
    inp = data.load_inputs()
    fig1_framework(); fig2_inputs(inp); fig3_heatmap(); fig4_tradeoff(); fig5_diurnal()
    fig6_peak_event(); fig7_transfer(); fig8_benchmark(); fig9_feed_in()
    print("figures written to", F)


if __name__ == "__main__":
    main()
