#!/usr/bin/env python3
"""make_figures.py -- figures of the Block-A-Mole paper.

Builds the paper's two figures (frontier.pdf and phase.pdf) from data that
already exist in the repository (no network access, no new simulation runs).
With --all it also draws robust.pdf, which plots results that the paper reports
in its text, and runs its checks.

  figures/phase.pdf       3.33 x 2.3 in (Figure 2, fig:phase)
      interval availability (T = 5) vs beta: exact lines for k_max = 4..64
      (exact.py) and the event-driven simulation
      <- simulations/results/E2_phase_transition.json
  figures/frontier.pdf    3.33 x 2.3 in (Figure 1, fig:frontier)
      exact frontier beta*(0.95, T), T = 1, 5, 20, and the time-average frontier
      vs k_max <- simulations/results/R2_frontiers.json
  figures/robust.pdf      7.0 x 1.95 in, 4 panels (only with --all; not a figure
                          of the paper)
      interval availability vs beta at k_max = 8: bursts, strategic timing with
      reserve, pooled diversification, mint-time exposure (the frontiers of
      Section 5.4 of the paper). R4/R5/R8 store
      frontiers and spot values rather than whole curves, so the curves are
      recomputed with simulations/code/exact.py (imported, not modified) and
      checked against every stored number that applies.

Checks. The script checks the plotted series against the stored results and
against the numbers that the paper reports; the table is printed to stdout and
the script exits with status 1 if any check fails. If `mutool` is installed,
each PDF is then checked for its page size, the smallest embedded font size
(>= 7 pt, sub- and superscripts included) and glyphs outside the page.

Run from the repository root:
    python3 paper/figures/make_figures.py [--outdir DIR] [--all]

Style: simulations/code/figstyle.py (STIX serif, Okabe-Ito colours). The PDFs
are written at their final size (no tight-bbox cropping): include them at
width=\\textwidth or \\columnwidth. All text is 8 pt and mathtext sub- and
superscripts are 7.2 pt, so the figures must not be scaled below about 97 %.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True        # never write __pycache__ into simulations/code

import numpy as np                                                # noqa: E402
import pandas as pd                                               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SIMCODE = os.path.join(ROOT, "simulations", "code")
RESULTS = os.path.join(ROOT, "simulations", "results")
sys.path.insert(0, SIMCODE)

import exact as ex                                                # noqa: E402
import figstyle                                                   # noqa: E402  (selects Agg)
import matplotlib                                                 # noqa: E402
import matplotlib._mathtext as _mathtext                          # noqa: E402
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.lines import Line2D                               # noqa: E402
from matplotlib.ticker import (FixedFormatter, FixedLocator,      # noqa: E402
                               LogLocator, MultipleLocator, NullFormatter,
                               NullLocator)

# canonical configuration: n = 8, lambda_a = lambda_intro = 1, mu = 3,
# k_max = 8, T = 5, alpha = 0.95; time unit 1/lambda_intro
N, LAM_A, MU, KMAX, T5, ALPHA = 8, 1.0, 3.0, 8, 5.0, 0.95
COL = figstyle.COL        # Okabe-Ito: blue, vermillion, green, pink, orange, sky blue
INK = "#333333"           # annotation text (text never wears a series colour)
REFC = "#595959"          # reference lines

# --------------------------------------------------------------------------- #
#  style
# --------------------------------------------------------------------------- #
BASE = 8.0                # every text element is set at 8 pt (final size)
# mathtext draws sub- and superscripts at 0.7 x the base size (8 pt -> 5.6 pt,
# below the 7 pt minimum). Raise the factor so that scripts are 0.9 x 8 =
# 7.2 pt. No label uses nested scripts.
SCRIPT_FACTOR = 0.9
MIN_PT = 7.0


def setup_style():
    figstyle.use_style()
    plt.rcParams.update({
        "font.size": BASE, "axes.labelsize": BASE, "axes.titlesize": BASE,
        "xtick.labelsize": BASE, "ytick.labelsize": BASE,
        "legend.fontsize": BASE, "legend.title_fontsize": BASE,
        "axes.titlepad": 3.0, "axes.labelpad": 2.5,
        "xtick.major.pad": 2.0, "ytick.major.pad": 2.0,
        "lines.linewidth": 1.3, "lines.markersize": 3.4,
        "legend.handlelength": 2.0, "legend.handletextpad": 0.45,
        "legend.labelspacing": 0.25, "legend.borderaxespad": 0.3,
        "legend.columnspacing": 0.9,
        "savefig.bbox": "standard",   # keep the exact page size (no tight crop)
        "savefig.pad_inches": 0.0,
        "pdf.fonttype": 42,           # embedded TrueType, no Type 3
    })
    if not hasattr(_mathtext, "SHRINK_FACTOR"):
        raise RuntimeError("matplotlib._mathtext.SHRINK_FACTOR not found; the "
                           "7 pt script-size fix needs updating")
    _mathtext.SHRINK_FACTOR = SCRIPT_FACTOR


# line styles and markers: identity never rests on colour alone
LS = ["-", (0, (5.0, 1.6)), (0, (3.2, 1.2, 1.0, 1.2)), (0, (1.1, 1.1)),
      (0, (6.5, 1.5, 1.5, 1.5, 1.5, 1.5))]
MK = ["o", "s", "^", "D", "v"]


def savefig(fig, outdir, name, written):
    path = os.path.join(outdir, name)
    # no creation date or producer strings: re-runs give identical files
    fig.savefig(path, metadata={"CreationDate": None, "Creator": None,
                                "Producer": None})
    plt.close(fig)
    written.append(path)
    return path


def axes_inches(fig, left, bottom, width, height):
    """Add axes placed in inches (exact layout, nothing outside the page)."""
    W, H = fig.get_size_inches()
    return fig.add_axes([left / W, bottom / H, width / W, height / H])


# --------------------------------------------------------------------------- #
#  check table
# --------------------------------------------------------------------------- #
CHECKS = []


def check(fig, item, plotted, stored, tol, note=""):
    """Record one comparison of a plotted value with a stored one."""
    if plotted is None or stored is None:
        ok, diff = (plotted is None and stored is None), float("nan")
    else:
        diff = abs(float(plotted) - float(stored))
        ok = diff <= tol
    CHECKS.append(dict(fig=fig, item=item, plotted=plotted, stored=stored,
                       diff=diff, tol=tol, ok=bool(ok), note=note))


def check_true(fig, item, cond, note=""):
    CHECKS.append(dict(fig=fig, item=item, plotted=None, stored=None,
                       diff=float("nan"), tol=None, ok=bool(cond), note=note))


def print_checks():
    def fmt(v):
        if v is None:
            return "-"
        if isinstance(v, (int, np.integer)):
            return str(v)
        return f"{float(v):.6g}"
    w = max(len(c["item"]) for c in CHECKS)
    npass = sum(c["ok"] for c in CHECKS)
    print(f"\nCHECK TABLE: plotted value vs stored result ({npass}/{len(CHECKS)} pass)")
    print(f"{'figure':<15} {'item':<{w}} {'plotted':>12} {'stored':>12} "
          f"{'|diff|':>9} {'tol':>7}  ok    source / note")
    for c in CHECKS:
        d = "-" if np.isnan(c["diff"]) else f"{c['diff']:.1e}"
        t = "-" if c["tol"] is None else f"{c['tol']:.0e}"
        print(f"{c['fig']:<15} {c['item']:<{w}} {fmt(c['plotted']):>12} "
              f"{fmt(c['stored']):>12} {d:>9} {t:>7}  "
              f"{'ok  ' if c['ok'] else 'FAIL'}  {c['note']}")
    return npass == len(CHECKS)


def load_json(name):
    with open(os.path.join(RESULTS, name)) as f:
        return json.load(f)


def crossing(x, y, level):
    """First x where the decreasing curve y(x) falls below `level` (linear
    interpolation between plotted grid points)."""
    y = np.asarray(y)
    i = int(np.argmax(y < level))
    if i == 0:
        return None
    x0, x1, y0, y1 = x[i - 1], x[i], y[i - 1], y[i]
    return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0))


# --------------------------------------------------------------------------- #
#  phase.pdf (fig:phase)
# --------------------------------------------------------------------------- #
def fig_phase(outdir, written):
    F = "phase"
    e2 = load_json("E2_phase_transition.json")
    r1 = load_json("R1_exact_validation.json")
    r2 = load_json("R2_frontiers.json")
    a5 = ex.addr_window(N, LAM_A, MU, T5)
    check(F, "address window at T=5", a5, r2["address_window"]["5.0"], 1e-12, "R2")
    check_true(F, "E2 configuration is canonical",
               (e2["n"], e2["lam_a"], e2["mu"], e2["alpha"]) == (N, LAM_A, MU, ALPHA))
    seeds = e2["_meta"]["seeds"]
    betas = np.array(e2["betas"])
    W, H = 3.33, 2.3
    fig = plt.figure(figsize=(W, H))
    ax = axes_inches(fig, 0.40, 0.40, W - 0.46, H - 0.48)
    bg = np.linspace(0.2, 2.0, 721)
    sel = slice(0, None, 2)                       # simulated points at beta = 0.2, 0.3, ..., 2.0
    ms = 3.3
    handles, max2se = [], 0.0
    for i, k in enumerate([4, 8, 16, 32, 64]):
        y = np.array([ex.name_window_constant(b, k, T5) * a5 for b in bg])
        ax.plot(bg, y, color=COL[i], ls=LS[i], lw=1.3, zorder=3)
        ye = np.array([ex.name_window_constant(b, k, T5) * a5 for b in betas])
        bs = r2["dense"]["interval"]["0.95|5.0"][r2["dense"]["kmax"].index(k)]
        check(F, f"k_max={k}: exact curve at stored beta*", ex.name_window_constant(bs, k, T5)
              * a5, ALPHA, 1e-9, f"R2 beta*(0.95,5)={bs:.4f}")
        check(F, f"k_max={k}: plotted crossing of alpha", crossing(bg, y, ALPHA), bs, 2e-3,
              "R2 (grid interpolation)")
        has_sim = str(k) in e2["curves"]
        if has_sim:
            stored = np.array(r1["E2"]["per_kmax"][str(k)]["exact_interval"])
            check(F, f"k_max={k}: exact at the 37 E2 betas, max diff",
                  float(np.max(np.abs(ye - stored))), 0.0, 1e-12, "R1 exact_interval")
            c = e2["curves"][str(k)]
            sv = np.array(c["interval"])
            se = np.array(c["interval_std"]) / np.sqrt(seeds)
            max2se = max(max2se, float(np.max(2 * se[sel])))
            ax.errorbar(betas[sel], sv[sel], yerr=2 * se[sel], fmt="none", ecolor=COL[i],
                        elinewidth=0.8, capsize=0, zorder=4)
            ax.plot(betas[sel], sv[sel], ls="none", marker=MK[i], ms=ms, mfc="white",
                    mec=COL[i], mew=0.85, zorder=5)
            st = r1["E2"]["per_kmax"][str(k)]["stats_interval"]
            check(F, f"k_max={k}: max |sim - exact| (37 points)", float(np.max(np.abs(sv - ye))),
                  st["max_abs_diff"], 1e-12, "R1 stats_interval")
            check(F, f"k_max={k}: max |z| = |sim - exact|/SE", float(np.max(np.abs(sv - ye) / se)),
                  st["max_abs_z"], 1e-9, "R1 stats_interval")
        handles.append(Line2D([], [], color=COL[i], ls=LS[i], lw=1.3,
                              marker=MK[i] if has_sim else None, ms=ms, mfc="white",
                              mec=COL[i], mew=0.85, label=fr"$k_{{\max}}={k}$"))
    st = r1["E2"]["stats_interval"]
    check(F, "all 148 E2 points: max |sim - exact|", max(
        r1["E2"]["per_kmax"][str(k)]["stats_interval"]["max_abs_diff"] for k in e2["kmaxes"]),
        0.0052, 5e-5, "paper: 0.0052")
    check(F, "all E2 points: share within 3 SE", st["frac_within_3se"], 0.993, 5e-4,
          "paper: 99.3%")
    ax.axhline(ALPHA, color=REFC, lw=0.8, ls=(0, (1.0, 1.4)), zorder=2)
    ax.axvline(1.0, color=REFC, lw=0.8, ls=(0, (4.0, 2.0)), zorder=2)
    ax.text(2.03, ALPHA + 0.012, r"$\alpha=0.95$", ha="right", va="bottom", color=INK)
    ax.text(1.03, 0.015, r"$\beta=1$", ha="left", va="bottom", color=INK)
    ax.text(0.20, 0.015, "exact (lines)\nsimulation (markers)", ha="left", va="bottom",
            color=INK, linespacing=1.1)
    ax.set_xlim(0.15, 2.05)
    ax.set_ylim(0.0, 1.03)
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_major_locator(MultipleLocator(0.2))
    ax.set_xlabel(r"burn ratio $\beta=\lambda_{\mathrm{burn}}/\lambda_{\mathrm{intro}}$")
    ax.set_ylabel(r"interval availability ($T=5$)")
    figstyle.tidy(ax)
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 0.92),
              frameon=False, handlelength=2.4)
    # the +-2 SE bars hide behind the markers when 2 SE < marker radius
    fig.canvas.draw()
    radius_pt = ms / 2
    pt_per_unit = ax.get_window_extent().height * 72 / fig.dpi / (1.03 - 0.0)
    check_true(F, "error bars (2 SE) shorter than the marker radius",
               max2se * pt_per_unit < radius_pt,
               f"largest 2 SE = {max2se:.4f} = {max2se * pt_per_unit:.2f} pt; "
               f"marker radius {radius_pt:.2f} pt")
    return savefig(fig, outdir, "phase.pdf", written)


# --------------------------------------------------------------------------- #
#  frontier.pdf (fig:frontier)
# --------------------------------------------------------------------------- #
# rounded values of the plotted curves that the paper reports in Section 5.2
# (PAPER_INTERVAL_T5, PAPER_TIMEAVG, PAPER_KMAX8_BY_T) and in the caption of
# Figure 1 (PAPER_FIRST_KMAX_ABOVE_1). SRC_INTERVAL_T5 marks two rounded R2
# values that the paper does not print and the paper's limit 1.016 of the
# T = 5 frontier, which the curve reaches at k_max = 256 to three decimals.
PAPER_INTERVAL_T5 = {2: 0.098, 4: 0.355, 8: 0.661, 16: 0.865, 32: 0.963, 64: 1.001, 128: 1.013,
            256: 1.016}
SRC_INTERVAL_T5 = {64: "R2 (rounded)", 128: "R2 (rounded)", 256: "paper: limit 1.016"}
PAPER_TIMEAVG = {2: 0.257, 4: 0.577, 8: 0.840, 16: 0.980, 32: 1.035}
PAPER_FIRST_KMAX_ABOVE_1 = {"time_average": 20, "1.0": 34, "5.0": 63, "20.0": 128}
PAPER_KMAX8_BY_T = {"1.0": 0.755, "5.0": 0.661, "20.0": 0.552}       # k_max = 8


def fig_frontier(outdir, written):
    F = "frontier"
    r2 = load_json("R2_frontiers.json")
    kd = np.array(r2["dense"]["kmax"])
    sel = kd <= 256
    k = kd[sel]
    ca_alpha = r2["c_a"] / ALPHA
    check(F, "c_a/alpha", ca_alpha, ex.addr_timeavg(N, LAM_A, MU) / ALPHA, 1e-12, "exact.py")
    check(F, "c_a/alpha", ca_alpha, 1.0526, 1e-4, "paper: 1.053")
    W, H = 3.33, 2.3
    fig = plt.figure(figsize=(W, H))
    ax = axes_inches(fig, 0.40, 0.40, W - 0.50, H - 0.48)
    ax.axhline(1.0, color=REFC, lw=0.8, zorder=1)
    ax.axhline(ca_alpha, color=REFC, lw=0.8, ls=(0, (1.0, 1.4)), zorder=1)
    ax.text(2.1, ca_alpha + 0.012, fr"$c_a/\alpha={ca_alpha:.3f}$", ha="left", va="bottom",
            color=INK)
    ax.text(2.1, 1.0 - 0.015, r"$\beta=1$", ha="left", va="top", color=INK)
    series = [("time average", "avg", "0.95", "#555555", LS[4], "time_average"),
              (r"$T=1$", "interval", "0.95|1.0", COL[0], LS[0], "1.0"),
              (r"$T=5$", "interval", "0.95|5.0", COL[1], LS[1], "5.0"),
              (r"$T=20$", "interval", "0.95|20.0", COL[2], LS[2], "20.0")]
    handles = []
    above1 = r2["min_kmax_beta_star_above_1"]["0.95"]
    for lab, kind, key, c, ls, tkey in series:
        vals = r2["dense"][kind][key]
        y = np.array([np.nan if v is None else v for v in vals], dtype=float)[sel]
        name = "time avg" if tkey == "time_average" else f"T={float(tkey):g}"
        check_true(F, f"{name}: stored dense curve complete for k_max<=256",
                   bool(np.all(np.isfinite(y))), f"{len(y)} points, k_max 2..256")
        ax.plot(k, y, color=c, ls=ls, lw=1.3, zorder=3)
        kc = above1["time_average"] if tkey == "time_average" else above1[tkey]["kmax"]
        ax.plot([kc], [1.0], ls="none", marker="o", ms=3.6, mfc="white", mec=c, mew=0.9,
                zorder=5)
        ax.text(kc, ca_alpha + 0.012, f"{kc}", ha="center", va="bottom", color=INK)
        handles.append(Line2D([], [], color=c, ls=ls, lw=1.3, label=lab))
        i_c = int(np.flatnonzero(k == kc)[0])
        check_true(F, f"{name}: curve crosses 1 at the marked k_max={kc}",
                   y[i_c] > 1.0 >= y[i_c - 1],
                   f"{y[i_c - 1]:.5f} at k_max={k[i_c - 1]}, {y[i_c]:.5f} at {kc}")
        check(F, f"{name}: smallest k_max with beta*>1", kc, PAPER_FIRST_KMAX_ABOVE_1[tkey], 0,
              "paper")
        for kk in (2, 4, 8, 32, 128, 256):
            if tkey == "time_average":
                rec, _ = ex.beta_star_avg(ALPHA, kk, N, LAM_A, MU)
            else:
                rec, _ = ex.frontier_interval(ALPHA, float(tkey), N, LAM_A, MU, kk)
            check(F, f"{name}: beta* at k_max={kk}", y[np.flatnonzero(k == kk)[0]], rec, 1e-8,
                  "recomputed with exact.py")
        facts = (PAPER_INTERVAL_T5 if tkey == "5.0"
                 else PAPER_TIMEAVG if tkey == "time_average" else {})
        for kk, v in facts.items():
            src = (SRC_INTERVAL_T5.get(kk, "paper (interval)") if tkey == "5.0"
                   else "paper (time average)")
            check(F, f"{name}: beta* at k_max={kk}", y[np.flatnonzero(k == kk)[0]], v, 5e-4,
                  src)
        if tkey in PAPER_KMAX8_BY_T:
            check(F, f"{name}: beta* at k_max=8", y[np.flatnonzero(k == 8)[0]],
                  PAPER_KMAX8_BY_T[tkey], 5e-4, "paper")
        check_true(F, f"{name}: below c_a/alpha for every k_max", np.max(y) <= ca_alpha,
                   f"max {np.max(y):.5f}")
    handles.append(Line2D([], [], ls="none", marker="o", ms=3.6, mfc="white", mec=INK,
                          mew=0.9, label=r"first $k_{\max}$ with $\beta^{\star}>1$"))
    ax.set_xscale("log", base=2)
    ax.set_xlim(2, 256)
    ticks = [2, 4, 8, 16, 32, 64, 128, 256]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FixedFormatter([str(t) for t in ticks]))
    ax.set_ylim(0.0, 1.16)
    ax.yaxis.set_major_locator(FixedLocator([0, 0.2, 0.4, 0.6, 0.8, 1.0]))
    ax.set_xlabel(r"buffer cap $k_{\max}$")
    ax.set_ylabel(r"frontier $\beta^{\star}$ ($\alpha=0.95$)")
    figstyle.tidy(ax)
    ax.xaxis.set_minor_locator(NullLocator())
    ax.legend(handles=handles, loc="lower right", frameon=False, handlelength=2.4)
    return savefig(fig, outdir, "frontier.pdf", written)


# --------------------------------------------------------------------------- #
#  robust.pdf (--all only; not a figure of the paper)
# --------------------------------------------------------------------------- #
def fig_robust(outdir, written):
    F = "robust"
    a5 = ex.addr_window(N, LAM_A, MU, T5)
    r1, r4 = load_json("R1_exact_validation.json"), load_json("R4_strategic_censor.json")
    r5, r8 = load_json("R5_diversification.json"), load_json("R8_mint_exposure.json")
    e7 = load_json("E7_bursty_burns.json")
    single = lambda b: ex.name_window_constant(b, KMAX, T5) * a5      # unit-burn pool

    # each series: legend label, plain name, curve function, stored beta*, paper value
    panels = []
    # (a) bursts: a takedown burns b names at once, same mean burn rate
    cur = []
    for b, fact in zip([1, 2, 4, 8], [0.661, 0.523, 0.314, 0.066]):
        ch = ex.batch_name_chain(KMAX, b)
        f = (lambda x, ch=ch: ch.window(T5, intro=1.0, disc=x) * a5)
        rec = r1["E7"]["per_b"][str(b)]
        cur.append((fr"$b={b}$", f"b={b}", f, rec["beta_star_exact_root"], fact))
        check(F, f"(a) b={b}: exact at the 25 E7 betas, max diff",
              float(np.max(np.abs(np.array([f(x) for x in e7["betas"]])
                                  - np.array(rec["exact_interval"])))), 0.0, 1e-12,
              "R1 E7 exact_interval")
    panels.append(("(a) bursts of $b$ names", cur, "paper"))
    # (b) strategic timing: Poisson censor vs strike-all, with reserve r
    cur = []
    chp = ex.strategic_chain(KMAX, "poisson")
    fp = (lambda x: chp.window(T5, intro=1.0, disc=x) * a5)
    pz = r4["policies"]["8"]["poisson"]
    cur.append(("Poisson", "Poisson", fp, pz["beta_star_interval"], 0.661))
    for b_, v in pz["interval_at_beta"].items():
        check(F, f"(b) Poisson: A at beta={b_}", fp(float(b_)), v, 1e-12, "R4 interval_at_beta")
        check(F, f"(b) Poisson = single pool at beta={b_}", fp(float(b_)), single(float(b_)),
              1e-10, "exact.py")
    for r, fact in zip([4, 2, 1, 0], [0.522, 0.367, 0.237, 0.064]):
        ch = ex.strategic_chain(KMAX, "strike_all", r=r)
        f = (lambda x, ch=ch: ch.window(T5, intro=1.0, disc=x) * a5)
        rec = r4["reserve"]["8"]["strike_all"][str(r)]
        cur.append((fr"strike-all, $r={r}$", f"strike-all r={r}", f, rec["beta_star_interval"],
                    fact))
        check(F, f"(b) strike-all r={r}: A at beta=0.5", f(0.5), rec["interval_at_beta_0.5"],
              1e-12, "R4 reserve")
        if r == 0:
            sa = r4["policies"]["8"]["strike_all"]
            check(F, "(b) strike-all r=0: beta*", rec["beta_star_interval"],
                  sa["beta_star_interval"], 1e-12, "R4 policies")
            for b_, v in sa["interval_at_beta"].items():
                check(F, f"(b) strike-all r=0: A at beta={b_}", f(float(b_)), v, 1e-12,
                      "R4 interval_at_beta")
    panels.append(("(b) strategic timing", cur, "paper"))
    # (c) pooled diversification: total k_max = 8 split over P providers
    cur = []
    sp = r5["by_kmax"]["8"]["single_pool_unit_burns"]
    check(F, "(c) single pool: A at beta=1", single(1.0), sp["interval_at_beta_1"], 1e-12, "R5")
    check(F, "(c) single pool: beta*", ex.frontier_interval(ALPHA, T5, N, LAM_A, MU, KMAX)[0],
          sp["beta_star_interval"], 1e-9, "R5")
    bchk = np.round(np.linspace(0.05, 3.0, 60), 4)              # R5's comparison grid
    for P, fact in zip([8, 4, 2, 1], [0.661, 0.311, 0.092, 0.008]):
        ch = ex.providers_chain(P, KMAX // P, "pooled")
        f = (lambda x, ch=ch: ch.window(T5, intro=1.0, disc=x) * a5)
        rec = r5["by_kmax"]["8"]["P"][str(P)]["pooled"]
        cur.append((fr"$P={P}$", f"P={P}", f, rec["beta_star_interval"], fact))
        check(F, f"(c) P={P}: A at beta=1", f(1.0), rec["interval_at_beta_1"], 1e-12, "R5")
        check(F, f"(c) P={P}: max (A - single pool) on R5 grid",
              max(f(x) - single(x) for x in bchk), rec["max_excess_over_single_interval"],
              1e-12, "R5 max_excess_over_single")
    panels.append(("(c) diversification over $P$", cur, "paper"))
    # (d) mint-time exposure: theta = infinity is the single pool minting at (1 - rho)
    cur = []
    for rho, fact in zip([0.0, 0.25, 0.5, 0.75, 0.9], [0.661, 0.510, 0.352, 0.185, 0.078]):
        f = (lambda x, rho=rho: ex.bd_window(*ex.name_rates_constant(KMAX, 1.0 - rho, x), T5)
             * a5)
        rec = r8["table"]["8"]["inf"][str(rho)]
        cur.append((fr"$\rho={rho:g}$", f"rho={rho:g}", f, rec["beta_star_interval"], fact))
    for lc in r8["theta_inf_limit_check"]:        # replicate R8's theta -> infinity check
        che = ex.exposure_chain(KMAX, lc["rho"])
        d = max(abs(che.window(T5, intro=1.0, disc=x, theta=lc["theta"])
                    - ex.bd_window(*ex.name_rates_constant(KMAX, 1 - lc["rho"], x), T5))
                for x in (0.1, 0.3, 0.6))
        check(F, f"(d) theta=inf vs chain, rho={lc['rho']:g}, theta={lc['theta']:g}", d,
              lc["max_abs_diff_window"], 1e-12, "R8 theta_inf_limit_check")
    panels.append((r"(d) mint-time exposure, $\theta=\infty$", cur, "paper"))

    W, H = 7.0, 1.95
    fig = plt.figure(figsize=(W, H))
    left, right, gap, bottom, top = 0.42, 0.06, 0.16, 0.38, 0.22
    pw = (W - left - right - 3 * gap) / 4
    axs = [axes_inches(fig, left + j * (pw + gap), bottom, pw, H - bottom - top)
           for j in range(4)]
    bg = np.geomspace(0.002, 2.0, 361)
    for j, (title, cur, fsrc) in enumerate(panels):
        ax = axs[j]
        tag = title.split(")")[0] + ")"
        if j == 2:   # the unit-burn single pool: a wide pale band under the P curves
            ax.plot(bg, [single(x) for x in bg], color="#bdbdbd", lw=3.6,
                    solid_capstyle="butt", zorder=2, label="single pool")
        for i, (lab, name, f, bstar, fact) in enumerate(cur):
            y = np.array([f(x) for x in bg])
            ax.plot(bg, y, color=COL[i], ls=LS[i], lw=1.25, zorder=3, label=lab)
            # dot: the frontier beta*, where the curve crosses alpha (stored value)
            ax.plot([bstar], [ALPHA], ls="none", marker="o", ms=3.3, mfc=COL[i], mec="white",
                    mew=0.5, zorder=5)
            check(F, f"{tag} {name}: curve at stored beta*", f(bstar), ALPHA, 1e-8,
                  f"stored beta*={bstar:.4g}")
            check(F, f"{tag} {name}: plotted crossing of alpha", crossing(bg, y, ALPHA), bstar,
                  2e-3 * bstar, "grid interpolation")
            check(F, f"{tag} {name}: beta*", bstar, fact, 5e-4, fsrc)   # paper: 3 decimals
        ax.axhline(ALPHA, color=REFC, lw=0.8, ls=(0, (1.0, 1.4)), zorder=1)
        ax.set_xscale("log")
        ax.set_xlim(0.002, 2.0)
        ax.set_ylim(0.0, 1.03)
        ax.xaxis.set_major_locator(FixedLocator([0.01, 0.1, 1.0]))
        ax.xaxis.set_major_formatter(FixedFormatter(["0.01", "0.1", "1"]))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10), numticks=12))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(MultipleLocator(0.2))
        ax.set_title(title, loc="left")
        ax.set_xlabel(r"burn ratio $\beta$")
        if j == 0:
            ax.set_ylabel(r"interval availability ($T=5$)")
        else:
            ax.tick_params(labelleft=False)
        figstyle.tidy(ax)
        ax.legend(loc="lower left", frameon=False, handlelength=2.0, borderaxespad=0.2)
    axs[0].text(0.0024, ALPHA - 0.02, r"$\alpha=0.95$", ha="left", va="top", color=INK)
    return savefig(fig, outdir, "robust.pdf", written)


# --------------------------------------------------------------------------- #
#  PDF checks: page size, smallest font, glyphs inside the page
# --------------------------------------------------------------------------- #
EXPECTED_SIZE = {"phase.pdf": (3.33, 2.3), "frontier.pdf": (3.33, 2.3),
                 "robust.pdf": (7.0, 1.95)}


def pdf_checks(paths):
    mutool = shutil.which("mutool")
    print("\nPDF CHECKS (sizes at final size; font sizes from the embedded text)")
    if not mutool:
        print("  mutool not found: font-size and page-bounds checks skipped")
        return True
    ok = True
    for p in paths:
        name = os.path.basename(p)
        out = subprocess.run([mutool, "draw", "-F", "stext", "-o", "-", p],
                             capture_output=True, text=True, check=True)
        root = ET.fromstring(out.stdout)
        page = root.find("page")
        pw, ph = float(page.get("width")), float(page.get("height"))
        sizes, small, outside = [], set(), []
        for font in root.iter("font"):
            sz = float(font.get("size"))
            for ch in font.iter("char"):
                sizes.append(sz)
                if sz < MIN_PT:
                    small.add((sz, ch.get("c")))
                q = [float(v) for v in ch.get("quad").split()]
                if min(q[0::2]) < 0 or max(q[0::2]) > pw or min(q[1::2]) < 0 or max(q[1::2]) > ph:
                    outside.append(ch.get("c"))
        ew, eh = EXPECTED_SIZE[name]
        size_ok = abs(pw - 72 * ew) < 0.05 and abs(ph - 72 * eh) < 0.05
        good = size_ok and not small and not outside
        ok &= good
        print(f"  {name}: page {pw / 72:.3f} x {ph / 72:.3f} in "
              f"({'ok' if size_ok else 'WRONG'}); {len(sizes)} glyphs, "
              f"{min(sizes):.2f}-{max(sizes):.2f} pt; below {MIN_PT:g} pt: {len(small)}; "
              f"outside the page: {len(outside)}  {'ok' if good else 'FAIL'}")
        if small:
            print("    small glyphs:", sorted(small)[:20])
        if outside:
            print("    outside:", outside[:20])
    return ok


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Build the paper's figures.")
    ap.add_argument("--outdir", default=os.path.join(ROOT, "figures"),
                    help="output directory (default: <repo>/figures)")
    ap.add_argument("--all", action="store_true",
                    help="also draw robust.pdf and run its checks")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    setup_style()
    written = []
    builds = (fig_frontier, fig_phase) + ((fig_robust,) if args.all else ())
    for build in builds:
        build(args.outdir, written)
    checks_ok = print_checks()
    pdf_ok = pdf_checks(written)
    print("\nwrote:", *[os.path.abspath(p) for p in written], sep="\n  ")
    print(f"python {sys.version.split()[0]}, matplotlib {matplotlib.__version__}, "
          f"numpy {np.__version__}, pandas {pd.__version__}")
    if not (checks_ok and pdf_ok):
        print("SOME CHECKS FAILED")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
