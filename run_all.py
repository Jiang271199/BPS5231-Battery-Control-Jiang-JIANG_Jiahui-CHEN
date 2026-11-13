#!/usr/bin/env python3
"""Reproduce every final result and figure (runtime depends on the machine).

    python run_all.py            # final pipeline 20-26 + tests
    python run_all.py --interim        # also run interim scripts 05-08 first
    python run_all.py --supplementary  # also run additional sensitivity scripts 27-29
"""
import os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INTERIM = ["05_exploratory_data_analysis.py", "06_no_battery_baseline.py",
           "07_pv_priority_battery.py", "08_interim_comparative_analysis.py"]
FINAL = ["20_run_rule_strategies.py", "21_run_s5_search.py", "22_run_search_benchmark.py",
         "23_run_mpc_and_bound.py", "24_run_sensitivity.py", "25_build_kpi_master.py",
         "26_make_publication_figures.py"]

SUPPLEMENTARY = ["27_check_common_initial_soc.py",
                 "28_battery_capacity_efficiency_sensitivity.py",
                 "29_purchase_tariff_sensitivity.py"]

steps = ((INTERIM if "--interim" in sys.argv else []) + FINAL
         + (SUPPLEMENTARY if "--supplementary" in sys.argv else []))
env = os.environ.copy()
env.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
for s in steps:
    t = time.time(); print(f"==> {s}", flush=True)
    subprocess.run([sys.executable, s], cwd=ROOT, check=True, env=env)
    print(f"    done in {time.time() - t:.0f} s", flush=True)
subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT, check=True, env=env)
