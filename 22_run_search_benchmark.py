#!/usr/bin/env python3
"""Equal-budget benchmark: ParEGO vs random search, 10 seeds each, 80 evaluations.

Search quality is measured by the exact 3-D hypervolume of each run's
evaluated set, with objectives normalised by the S1 calibration KPIs and a
reference point fixed in advance at (1.5, 1.5, 1.01) x S1. The first 20
samples of each seed are shared by both methods.
"""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from battery_study import config, data, controllers as C, metrics, evaluate as E, search

OUT = config.RESULTS / "s5_multiobjective"
SEEDS = [config.S5_SEED] + list(range(101, 110))
REF = np.array([1.5, 1.5, 1.01])
KEYS = list(metrics.KEYS)


def one(args):
    method, seed = args
    inp = data.load_inputs(); cal = data.calibration_import(inp)
    return search.run(inp, cal, C.s5_bounds(inp, cal), method, seed)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(m, s) for m in ("parego", "random") for s in SEEDS]
    with ProcessPoolExecutor(max_workers=2) as ex:
        rows = [r for res in ex.map(one, jobs) for r in res]
    allr = pd.DataFrame(rows); allr.to_csv(OUT / "benchmark_all_evaluations.csv", index=False)
    inp = data.load_inputs()
    s1 = E.score_calibration(inp, C.s1_pv_priority(inp))
    scale = np.array([s1[k] for k in KEYS])
    curves = []
    for (m, s), g in allr.groupby(["method", "seed"]):
        y = g.sort_values("evaluation")[KEYS].to_numpy() / scale
        for n in range(1, len(y) + 1):
            curves.append({"method": m, "seed": s, "evaluations": n,
                           "hypervolume": metrics.hypervolume_3d(y[:n], REF)})
    curves = pd.DataFrame(curves); curves.to_csv(OUT / "benchmark_hypervolume_curves.csv", index=False)
    final = curves.loc[curves.evaluations.eq(search.N_TOTAL)]
    summ = final.groupby("method").hypervolume.describe()[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    best = allr.groupby(["method", "seed"])[KEYS].min().groupby("method").median()
    pv = final.pivot(index="seed", columns="method", values="hypervolume")
    wins = int((pv.parego > pv.random).sum())
    from scipy.stats import wilcoxon
    stat = wilcoxon(pv.parego, pv.random)
    summ["paired_wins_parego"] = [wins if i == "parego" else len(pv) - wins for i in summ.index]
    summ["wilcoxon_p_two_sided"] = stat.pvalue
    summ = summ.join(best.add_prefix("median_best_"))
    summ.to_csv(OUT / "benchmark_summary.csv")
    print(summ.round(4).T.to_string())


if __name__ == "__main__":
    main()
