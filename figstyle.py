"""Shared figure style for the jump experiments.

One place fixes typography, palette, panel geometry and export, so that every figure in the paper
reads as one family and prints correctly in grayscale. Conventions follow the venue: no titles
inside the axes, since the caption names the figure; short axis labels; direct labels in place of
legends where a legend would repeat the curve order; Wilson intervals on every rate; and the count
behind a rate written next to it whenever the reader needs it to judge the interval.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ---------------------------------------------------------------- geometry (inches)
TEXT_W = 5.50          # full text width of the venue template
HALF_W = 2.68          # side-by-side panel
GOLDEN = 0.618

# ---------------------------------------------------------------- palette
# Okabe and Ito, safe for the common colour vision deficiencies and separable in grayscale.
BLUE, ORANGE, GREEN, YELLOW = "#0072B2", "#E69F00", "#009E73", "#F0E442"
SKY, VERMILION, PURPLE, GREY = "#56B4E9", "#D55E00", "#CC79A7", "#8C8C8C"
INK, RULE = "#1A1A1A", "#B0B0B0"

CLASS_COLOR = {"ADM": GREEN, "KAN": VERMILION, "LAN": VERMILION, "RAN": PURPLE,
               "VALID_OTHER": YELLOW, "RULE_VIOL": SKY, "INVALID": "#C9C9C9"}
CLASS_LABEL = {"ADM": "admissible", "KAN": "canonical default", "LAN": "left Kan", "RAN": "right Kan",
               "VALID_OTHER": "other valid", "RULE_VIOL": "rule violation", "INVALID": "unparsable"}
FAMILY_COLOR = {"closed": BLUE, "reasoning": GREEN, "plain": VERMILION}
FAMILY_LABEL = {"closed": "closed frontier", "reasoning": "open, reasoning", "plain": "open, no reasoning"}
FAMILY_MARKER = {"closed": "o", "reasoning": "s", "plain": "^"}

# models whose answers carry no chain of thought
PLAIN_MODELS = {"RedHatAI/Llama-3.3-70B-Instruct-FP8-dynamic",
                "RedHatAI/Qwen2.5-72B-Instruct-FP8-dynamic"}
CLOSED_MODELS = {"anthropic/claude-sonnet-5", "deepseek/deepseek-v4-pro-0813",
                 "google/gemini-3.1-pro-preview", "openai/gpt-5.6-luna-pro"}


def family_of(model):
    if model in CLOSED_MODELS:
        return "closed"
    return "plain" if model in PLAIN_MODELS else "reasoning"


def use_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["STIX Two Text", "STIXGeneral", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "xtick.direction": "out", "ytick.direction": "out",
        "lines.linewidth": 1.0, "lines.markersize": 3.5,
        "grid.color": RULE, "grid.linewidth": 0.4, "grid.alpha": 0.5,
        "legend.frameon": False, "legend.handlelength": 1.4,
        "legend.handletextpad": 0.5, "legend.columnspacing": 1.1, "legend.borderaxespad": 0.2,
        "figure.dpi": 200, "savefig.dpi": 400, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def wilson(k, n, z=1.96):
    """Point estimate and 95% interval, clamped so that the interval always contains the point."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, min(max(0.0, c - h), p), max(min(1.0, c + h), p)


def err(p, lo, hi):
    """Asymmetric error bar lengths for matplotlib, never negative."""
    return [[max(0.0, p - lo)], [max(0.0, hi - p)]]


def ygrid(ax, axis="y"):
    ax.grid(axis=axis, which="major", linestyle=(0, (1, 2)), zorder=0)
    ax.set_axisbelow(True)


def rate_axis(ax, axis="y", label=None):
    setter = ax.set_ylim if axis == "y" else ax.set_xlim
    ticks = ax.set_yticks if axis == "y" else ax.set_xticks
    setter(-0.02, 1.03)
    ticks([0, 0.25, 0.5, 0.75, 1.0])
    fmt = ["0", ".25", ".5", ".75", "1"]
    (ax.set_yticklabels if axis == "y" else ax.set_xticklabels)(fmt)
    if label:
        (ax.set_ylabel if axis == "y" else ax.set_xlabel)(label)
    ygrid(ax, axis)


def panel_tag(ax, text, dx=-0.055, dy=1.04):
    ax.text(dx, dy, text, transform=ax.transAxes, fontsize=8.5, fontweight="bold", va="bottom", ha="left")


def family_legend(ax, families=("closed", "reasoning", "plain"), **kw):
    handles = [Line2D([], [], color=FAMILY_COLOR[f], marker=FAMILY_MARKER[f], linestyle="none",
                      markersize=3.5, label=FAMILY_LABEL[f]) for f in families]
    ax.legend(handles=handles, **kw)


def class_legend(ax, classes, ncol=3, **kw):
    handles = [Patch(facecolor=CLASS_COLOR[c], edgecolor="none", label=CLASS_LABEL[c]) for c in classes]
    ax.legend(handles=handles, ncol=ncol, **kw)


def save(fig, out_dir, name):
    import os
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out_dir, f"{name}.{ext}"))
    plt.close(fig)
