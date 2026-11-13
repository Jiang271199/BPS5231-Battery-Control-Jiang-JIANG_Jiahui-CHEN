"""Study-wide constants. Every script imports these instead of re-deriving them."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "processed" / "building_5_hourly_inputs.csv"
SCHEMA_FILE = ROOT / "data" / "raw" / "schema.json"
RESULTS = ROOT / "results" / "final"
FIGURES = ROOT / "figures" / "publication"

N_STEPS = 8760
# Source order runs August -> July. Step 0 is a leading July wrap-around hour.
CALIBRATION = (1, 5833)      # steps 1..5832, August-March (parameter selection only)
HOLDOUT = (5833, 8760)       # steps 5833..8759, April-July (never used for selection)
FULL_YEAR = (0, 8760)
PERIODS = {"calibration": CALIBRATION, "holdout": HOLDOUT, "full_year": FULL_YEAR}

# Boundary convention used for every reported result: periodic (cyclic) SOC.
# The initial SOC of a window equals its final SOC, so no strategy gains or
# loses stored energy across the window boundary.
PERIODIC_TOL_KWH = 1e-4
PERIODIC_MAX_PASSES = 12

S5_SEED = 5231
