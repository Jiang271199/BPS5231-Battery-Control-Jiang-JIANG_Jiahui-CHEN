"""Rebuild the selected rule-based policies from saved parameter files."""
from __future__ import annotations
import json
import pandas as pd
from . import config, data, controllers as C


def rule_policies(inp):
    sel = json.loads((config.RESULTS / "rule_strategies" / "selected_parameters.json").read_text())
    p2, p3, p4 = sel["S2 peak shaving"], sel["S3 price response"], sel["S4 carbon response"]
    pol = {
        "S1 PV priority": C.s1_pv_priority(inp),
        "S2 peak shaving": C.s2_peak_shaving(inp, p2["target_kw"], p2["reserve_fraction"], p2["ceiling_kw"], p2["charge_hours"]),
        "S3 price response": C.s3_price_response(inp, p3["low"], p3["high"], p3["max_soc"], p3["ceiling_kw"]),
        "S4 carbon response": C.s4_carbon_response(inp, p4["low"], p4["high"], p4["max_soc"], p4["ceiling_kw"]),
    }
    cal = data.calibration_import(inp); bounds = C.s5_bounds(inp, cal)
    s5 = pd.read_csv(config.RESULTS / "s5_multiobjective" / "S5_selected_parameters.csv")
    s5 = s5.drop_duplicates(subset="evaluation")  # min_cost and min_carbon may be the same candidate
    for _, r in s5.iterrows():
        pol[f"S5 {r.solution}"] = C.s5_score_policy(inp, r.to_dict(), bounds)
    return pol
