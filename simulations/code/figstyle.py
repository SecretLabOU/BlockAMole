"""
figstyle.py -- shared styling for every paper figure.

Centralizes the matplotlib style (serif STIX font, Okabe-Ito palette), the
"legend on top, spread to full width" helper, heatmap polish (full frame, no
grid), and small contrast utilities, so all figures look identical and are
tweaked in one place.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

_STYLE = os.path.join(os.path.dirname(__file__), "paper.mplstyle")

# matched Okabe-Ito palette (same order as the prop_cycle in paper.mplstyle)
COL = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]
GRIDGRAY = "#9aa0a6"


def use_style():
    """Apply the shared paper style."""
    plt.style.use(_STYLE)


def toplegend(ax, ncol, fontsize=8, pad=0.02):
    """Horizontal legend above the axes, spread to the full axes width."""
    ax.legend(bbox_to_anchor=(0, 1.0 + pad, 1, 0.12), loc="lower left",
              mode="expand", ncol=ncol, frameon=False, fontsize=fontsize,
              borderaxespad=0, handletextpad=0.5, columnspacing=1.1)


def tidy(ax):
    """Final polish for a line-plot axis: minor ticks and a soft two-level grid.
    Call after any set_xscale/set_yscale, since AutoMinorLocator is linear-only."""
    if ax.get_xscale() == "linear":
        ax.xaxis.set_minor_locator(AutoMinorLocator())
    if ax.get_yscale() == "linear":
        ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.grid(True, which="major", color=GRIDGRAY, alpha=0.22, linewidth=0.5)
    ax.grid(True, which="minor", color=GRIDGRAY, alpha=0.10, linewidth=0.4)
    ax.tick_params(which="both", direction="out")


def heatmap_frame(ax):
    """Heatmaps look best fully framed and gridless (the despined line-plot look
    does not apply). Restore all four spines and drop the grid."""
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(0.8)
        s.set_edgecolor("#444444")
    ax.tick_params(which="minor", bottom=False, top=False,
                   left=False, right=False)


def contrast_color(value, vmin, vmax, thresh=0.55):
    """Pick black/white text for legibility over a sequential colormap cell."""
    frac = (value - vmin) / (vmax - vmin + 1e-12)
    return "white" if frac < thresh else "black"


def dark_halo():
    """A translucent dark box to keep light text legible over bright regions."""
    return dict(facecolor="black", alpha=0.35, edgecolor="none",
                boxstyle="round,pad=0.25")
