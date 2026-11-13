"""One publication style for every figure: white background, portable fonts,
fixed colour per strategy (identity never depends on figure or rank)."""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
COLORS = {  # categorical slots validated for CVD separation (dataviz validator)
    "S0": "#b5b4ad", "S1": "#3b3a37", "S2": "#2a78d6", "S3": "#eb6834",
    "S4": "#1baf7a", "S5": "#6250d6", "S6": "#008300", "LP": "#0b0b0b",
}
MARKERS = {"S0": "s", "S1": "o", "S2": "D", "S3": "^", "S4": "v", "S5": "P", "S6": "*"}
DIVERGING = ["#184f95", "#5598e7", "#cde2fb", "#f0efec", "#f6c9c8", "#e66767", "#a32b2b"]

FULL_WIDTH_IN = 7.0     # two-column page width
COLUMN_WIDTH_IN = 3.4


def _font():
    for name in ("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"):
        try:
            font_manager.findfont(name, fallback_to_default=False)
            return name
        except ValueError:
            continue
    return "sans-serif"


def apply():
    plt.rcParams.update({
        "font.family": _font(), "font.size": 8.5, "axes.titlesize": 9.5, "axes.labelsize": 8.5,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "lines.linewidth": 1.6,
        "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def family(strategy: str) -> str:
    return "LP" if strategy.startswith("LP") else strategy.split()[0]


def save(fig, path_stem):
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path_stem.with_suffix(".png"))
    fig.savefig(path_stem.with_suffix(".pdf"))
    plt.close(fig)
