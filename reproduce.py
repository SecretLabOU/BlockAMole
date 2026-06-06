#!/usr/bin/env python3
"""
reproduce.py -- Master reproduction script.

  "Block-A-Mole: The Sustainability Frontier of Moving-Target Censorship Resistance."

Runs the full rotation-game simulation suite and regenerates *every* figure and
results table from the paper, written with public-release filenames numbered
exactly as they appear in the paper:

    <outdir>/figure_1.pdf ... figure_8.pdf   vector PDF, one per paper figure
    <outdir>/table_1.txt  ... table_4.txt    plain-text, one per paper table

Multi-panel paper figures are rendered as a single composite PDF: figure_4.pdf
holds panels (a),(b) and figure_5.pdf holds panels (a)-(d), matching the paper.
The raw per-experiment data behind the figures is also written to
<outdir>/data/*.json unless --no-data is given.

The numerical model lives in three dependency-light modules shipped alongside
this script: theory.py (closed forms), rotation_game.py (the event-driven
simulator), and censor_models.py (calibrated adversary presets). This file is
the single entry point that drives them end to end.

Usage
-----
    python3 reproduce.py              # full sweeps (paper settings; ~10-15 min)
    python3 reproduce.py --quick      # smaller sweeps / shorter horizons (fast)
    python3 reproduce.py --outdir out # choose an output directory
    python3 reproduce.py --no-data    # skip writing the raw JSON

Requirements: Python >= 3.9 with numpy, scipy, matplotlib (see requirements.txt).

License: MIT (code) / CC BY 4.0 (generated data). Released for open reuse as a
shared, theory-grounded testbed for the censorship-resistance community.
"""

import argparse
import json
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator

import theory
from censor_models import CENSORS
from rotation_game import (GameParams, run, simulate_address, simulate_domain,
                           simulate_provider, combine, interval_up_probability,
                           intersect, _merge, _simulate_birth_death)

# canonical defender configuration (strong address layer -> domain layer binds)
N, MU, LAM_A, KMAX = 8, 3.0, 1.0, 8


# =========================================================================== #
#  Figure styling (self-contained; mirrors the paper's matplotlib style)
# =========================================================================== #
# colour-blind-safe Okabe-Ito palette (reordered for contrast)
COL = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]
GRIDGRAY = "#9aa0a6"

# reference-line styling, shared across figures
REF = dict(color="#3a3a3a", lw=1.0, alpha=0.7)                   # threshold lines
SEP = dict(color="#7a7a7a", ls=(0, (4, 3)), lw=1.0, alpha=0.85)  # beta = 1 marker

_RC = {
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "TeX Gyre Termes", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9.5,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "text.color": "#1a1a1a", "axes.labelcolor": "#1a1a1a",
    "axes.edgecolor": "#595959", "axes.linewidth": 0.9,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "xtick.color": "#595959", "ytick.color": "#595959",
    "xtick.direction": "out", "ytick.direction": "out",
    "xtick.major.size": 3.2, "ytick.major.size": 3.2,
    "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "xtick.minor.size": 1.8, "ytick.minor.size": 1.8,
    "xtick.minor.width": 0.6, "ytick.minor.width": 0.6,
    "xtick.minor.visible": True, "ytick.minor.visible": True,
    "axes.grid": True, "grid.color": GRIDGRAY, "grid.alpha": 0.22,
    "grid.linewidth": 0.5, "grid.linestyle": "-",
    "lines.linewidth": 1.8, "lines.markersize": 4, "lines.markeredgewidth": 0.9,
    "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
    "lines.dash_capstyle": "round",
    "legend.frameon": False, "legend.handlelength": 1.7,
    "legend.handletextpad": 0.5, "legend.columnspacing": 1.1,
    "legend.labelspacing": 0.3,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "figure.dpi": 150, "savefig.dpi": 600, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02, "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.prop_cycle": plt.cycler("color", COL),
}


def use_style():
    plt.rcParams.update(_RC)


def toplegend(ax, ncol, fontsize=8, pad=0.02):
    """Horizontal legend above the axes, spread to the full axes width."""
    ax.legend(bbox_to_anchor=(0, 1.0 + pad, 1, 0.12), loc="lower left",
              mode="expand", ncol=ncol, frameon=False, fontsize=fontsize,
              borderaxespad=0, handletextpad=0.5, columnspacing=1.1)


def complegend(ax, ncol, fs=6.6):
    """Compact top legend for the small single-row composite panels."""
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=ncol,
              frameon=False, fontsize=fs, handlelength=1.0, columnspacing=0.7,
              handletextpad=0.3, borderaxespad=0.12)


def tidy(ax):
    """Minor ticks and a soft two-level grid for a line-plot axis.
    Call after any set_xscale/set_yscale (AutoMinorLocator is linear-only)."""
    if ax.get_xscale() == "linear":
        ax.xaxis.set_minor_locator(AutoMinorLocator())
    if ax.get_yscale() == "linear":
        ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.grid(True, which="major", color=GRIDGRAY, alpha=0.22, linewidth=0.5)
    ax.grid(True, which="minor", color=GRIDGRAY, alpha=0.10, linewidth=0.4)
    ax.tick_params(which="both", direction="out")


def heatmap_frame(ax):
    """Heatmaps look best fully framed and gridless."""
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(0.8)
        s.set_edgecolor("#444444")
    ax.tick_params(which="minor", bottom=False, top=False, left=False, right=False)


def contrast_color(value, vmin, vmax, thresh=0.55):
    frac = (value - vmin) / (vmax - vmin + 1e-12)
    return "white" if frac < thresh else "black"


def dark_halo():
    return dict(facecolor="black", alpha=0.35, edgecolor="none",
                boxstyle="round,pad=0.25")


def _open_marker(color):
    """Hollow data marker with a coloured edge (clean sim-vs-theory look)."""
    return dict(mfc="white", mec=color, mew=1.0)


def _panel_tag(ax, text):
    """Bold panel identifier, e.g. (a), for the composite figures."""
    ax.set_title(text, fontsize=9, fontweight="bold", loc="left", pad=10)


# =========================================================================== #
#  Experiments  (E1-E10): each returns a JSON-serializable result dict
# =========================================================================== #
def _avg(rows, key):
    return float(np.mean([r[key] for r in rows]))


def _std(rows, key):
    return float(np.std([r[key] for r in rows]))


def _beta_star(betas, interval, alpha):
    """Largest beta whose interval availability >= alpha (None if never)."""
    bstar = None
    for b, v in zip(betas, interval):
        if v >= alpha:
            bstar = b
    return bstar


def exp_ip_geometric(seeds, quick):
    """E1: P[all addresses blocked] vs n, simulation vs geometric theory."""
    ns = list(range(1, 11))
    ratios = [0.5, 1.0, 2.0, 4.0]   # mu / lam_a
    lam_a = 1.0
    horizon = 6000.0 if quick else 12000.0
    out = {"ns": ns, "ratios": ratios, "curves": {}}
    for ratio in ratios:
        mu = ratio * lam_a
        sim, th = [], []
        for n in ns:
            p = GameParams(n=n, mu=mu, lam_a=lam_a, horizon=horizon)
            pz = float(np.mean([simulate_address(p, seed=s)[1]
                                for s in range(seeds)]))
            sim.append(pz)
            th.append(theory.ip_denial(n, lam_a, mu))
        out["curves"][str(ratio)] = {"sim": sim, "theory": th}
    return out


def exp_phase_transition(seeds, quick):
    """E2: interval availability vs beta for several domain buffers kmax."""
    betas = list(np.round(np.linspace(0.2, 2.0, 19 if quick else 37), 4))
    kmaxes = [4, 8, 16, 32]
    alpha = 0.95
    horizon = 15000.0 if quick else 30000.0
    acc = {(b, k): [] for k in kmaxes for b in betas}
    for s in range(seeds):
        p_addr = GameParams(n=N, mu=MU, lam_a=LAM_A, horizon=horizon)
        a_downs, a_pz = simulate_address(p_addr, seed=10_000 + s)
        for k in kmaxes:
            for b in betas:
                p = GameParams(n=N, mu=MU, lam_a=LAM_A, lam_intro=1.0,
                               lam_disc=b, kmax=k, horizon=horizon)
                d_downs, d_pz, d_mk = simulate_domain(
                    p, seed=int(1e6 + s * 1000 + k * 37 + b * 101))
                acc[(b, k)].append(combine(p, a_downs, a_pz, d_downs, d_pz, d_mk))
    out = {"betas": betas, "kmaxes": kmaxes, "alpha": alpha,
           "n": N, "mu": MU, "lam_a": LAM_A, "curves": {}}
    for k in kmaxes:
        iv = [_avg(acc[(b, k)], "interval_avail") for b in betas]
        iv_std = [_std(acc[(b, k)], "interval_avail") for b in betas]
        ta = [_avg(acc[(b, k)], "time_avg_avail") for b in betas]
        th = [theory.stationary_availability(b, N, LAM_A, MU, k) for b in betas]
        out["curves"][str(k)] = {"interval": iv, "interval_std": iv_std,
                                 "time_avg": ta, "theory_timeavg": th,
                                 "beta_star_interval": _beta_star(betas, iv, alpha)}
    return out


def exp_mu_heatmap(seeds, quick):
    """E3: availability over a (beta, mu/lam_a) grid -> mu is not the lever."""
    betas = list(np.round(np.linspace(0.3, 1.8, 13 if quick else 25), 4))
    ratios = list(np.round(np.linspace(0.25, 8.0, 12 if quick else 20), 4))
    lam_a, n, kmax = 1.0, N, KMAX
    horizon = 12000.0 if quick else 20000.0
    grid_ta = np.zeros((len(ratios), len(betas)))
    grid_iv = np.zeros((len(ratios), len(betas)))
    sd = max(8, seeds // 2)
    for s in range(sd):
        addr = {}
        for ri, ratio in enumerate(ratios):
            p = GameParams(n=n, mu=ratio * lam_a, lam_a=lam_a, horizon=horizon)
            addr[ri] = simulate_address(p, seed=20_000 + s * 97 + ri)
        dom = {}
        for bi, b in enumerate(betas):
            p = GameParams(n=n, lam_a=lam_a, lam_intro=1.0, lam_disc=b,
                           kmax=kmax, horizon=horizon)
            dom[bi] = simulate_domain(p, seed=30_000 + s * 131 + bi)
        for ri, ratio in enumerate(ratios):
            a_downs, a_pz = addr[ri]
            for bi, b in enumerate(betas):
                d_downs, d_pz, d_mk = dom[bi]
                p = GameParams(n=n, mu=ratio * lam_a, lam_a=lam_a, lam_disc=b,
                               kmax=kmax, horizon=horizon)
                m = combine(p, a_downs, a_pz, d_downs, d_pz, d_mk)
                grid_ta[ri, bi] += m["time_avg_avail"]
                grid_iv[ri, bi] += m["interval_avail"]
    grid_ta /= sd
    grid_iv /= sd
    return {"betas": betas, "ratios": ratios, "n": n, "kmax": kmax,
            "time_avg": grid_ta.tolist(), "interval": grid_iv.tolist()}


def exp_beta_star_grid(seeds, quick):
    """E4: closed-form beta*(n, kmax) under each calibrated censor."""
    ns = [2, 4, 6, 8, 12]
    kmaxes = [2, 4, 8, 16, 32]
    alpha = 0.95
    out = {"ns": ns, "kmaxes": kmaxes, "alpha": alpha, "censors": {}}
    for key, c in CENSORS.items():
        grid = []
        for n in ns:
            row = []
            for kmax in kmaxes:
                bstar = theory.beta_star_timeavg(alpha, n, c["lam_a"], MU, kmax)
                row.append(None if (bstar is None or np.isnan(bstar)) else float(bstar))
            grid.append(row)
        out["censors"][key] = {"label": c["label"], "beta_star": grid}
    return out


def exp_domain_economy(seeds, quick):
    """E5: required introduction rate vs censor domain-block rate."""
    alpha = 0.95
    betas = list(np.round(np.linspace(0.2, 1.2, 11 if quick else 21), 4))
    horizon = 15000.0 if quick else 30000.0
    iv = []
    for b in betas:
        p = GameParams(n=N, mu=MU, lam_a=LAM_A, lam_intro=1.0, lam_disc=b,
                       kmax=KMAX, horizon=horizon)
        iv.append(run(p, seeds=seeds)["interval_avail"])
    bstar = _beta_star(betas, iv, alpha) or 0.2
    burn_per_day = [5, 10, 25, 50, 100, 200, 400]
    required_intro = [bd / bstar for bd in burn_per_day]
    cost_per_domain = 0.01   # USD blended; free-tier sub-domains ~$0, registrable ~cents
    daily_cost = [r * cost_per_domain for r in required_intro]
    return {"alpha": alpha, "beta_star_interval": bstar, "kmax": KMAX,
            "betas": betas, "interval": iv,
            "burn_per_day": burn_per_day, "required_intro_per_day": required_intro,
            "cost_per_domain": cost_per_domain, "daily_cost": daily_cost}


def exp_session_length(seeds, quick):
    """E6: the interval frontier beta*(alpha,T) vs session length T."""
    betas = list(np.round(np.linspace(0.2, 1.4, 25 if quick else 49), 4))
    Ts_frontier = list(np.round(np.geomspace(1.0, 20.0, 12 if quick else 20), 3))
    Ts_display = [1.0, 5.0, 20.0]
    Ts = sorted(set(Ts_frontier) | set(Ts_display))
    alphas = [0.90, 0.95, 0.99]
    horizon = 20000.0 if quick else 40000.0
    warmup = 0.1 * horizon
    acc = {b: {T: [] for T in Ts} for b in betas}
    for s in range(seeds):
        p_addr = GameParams(n=N, mu=MU, lam_a=LAM_A, horizon=horizon)
        a_downs, _ = simulate_address(p_addr, seed=40_000 + s)
        for b in betas:
            p = GameParams(n=N, mu=MU, lam_a=LAM_A, lam_intro=1.0, lam_disc=b,
                           kmax=KMAX, horizon=horizon)
            d_downs, _, _ = simulate_domain(p, seed=int(5e6 + s * 1000 + b * 101))
            alld = _merge(list(a_downs) + list(d_downs))
            for T in Ts:
                acc[b][T].append(
                    interval_up_probability(alld, warmup, horizon, T))
    curves = {str(T): [float(np.mean(acc[b][T])) for b in betas] for T in Ts}
    bstar = {}
    for a in alphas:
        bstar[str(a)] = {}
        for T in Ts_frontier:
            bs = None
            for b, v in zip(betas, curves[str(T)]):
                if v >= a:
                    bs = b
            bstar[str(a)][str(T)] = bs
    return {"betas": betas, "Ts": Ts, "Ts_frontier": Ts_frontier,
            "Ts_display": Ts_display, "alphas": alphas, "kmax": KMAX,
            "curves": curves, "beta_star": bstar}


def exp_bursty_burns(seeds, quick):
    """E7: robustness to correlated (bursty) burns at fixed mean burn rate."""
    betas = list(np.round(np.linspace(0.2, 1.4, 13 if quick else 25), 4))
    batches = [1, 2, 4, 8]
    alpha = 0.95
    horizon = 15000.0 if quick else 30000.0
    acc = {(b, bb): [] for bb in batches for b in betas}
    for s in range(seeds):
        p_addr = GameParams(n=N, mu=MU, lam_a=LAM_A, horizon=horizon)
        a_downs, a_pz = simulate_address(p_addr, seed=50_000 + s)
        for bb in batches:
            for b in betas:
                p = GameParams(n=N, mu=MU, lam_a=LAM_A, lam_intro=1.0,
                               lam_disc=b, kmax=KMAX, burn_batch=bb,
                               horizon=horizon)
                d_downs, d_pz, d_mk = simulate_domain(
                    p, seed=int(6e6 + s * 1000 + bb * 311 + b * 101))
                acc[(b, bb)].append(
                    combine(p, a_downs, a_pz, d_downs, d_pz, d_mk))
    out = {"betas": betas, "batches": batches, "alpha": alpha, "kmax": KMAX,
           "curves": {}}
    for bb in batches:
        iv = [_avg(acc[(b, bb)], "interval_avail") for b in betas]
        out["curves"][str(bb)] = {"interval": iv,
                                  "beta_star_interval": _beta_star(betas, iv, alpha)}
    return out


def exp_budget_allocation(seeds, quick):
    """E8: the censor's optimal Stackelberg budget split (validates Prop. 1)."""
    B = 1.5
    ns = [1, 2, 4, 8]
    fracs = list(np.round(np.linspace(0.05, 0.97, 13 if quick else 25), 4))
    horizon = 15000.0 if quick else 30000.0
    out = {"B": B, "ns": ns, "fracs": fracs, "kmax": KMAX, "mu": MU, "curves": {}}
    for n in ns:
        iv = []
        for f in fracs:
            lam_disc = f * B
            lam_a = max(1e-6, (1.0 - f) * B / n)
            p = GameParams(n=n, mu=MU, lam_a=lam_a, lam_intro=1.0,
                           lam_disc=lam_disc, kmax=KMAX, horizon=horizon)
            iv.append(run(p, seeds=seeds)["interval_avail"])
        fstar = fracs[int(np.argmin(iv))]   # censor's best response
        out["curves"][str(n)] = {"interval": iv, "f_star": fstar}
    return out


def exp_multiprovider(seeds, quick):
    """E9: diversifying domains across P independent providers (validates P3)."""
    betas = list(np.round(np.linspace(0.2, 1.4, 13 if quick else 25), 4))
    Ps = [1, 2, 4, 8]
    alpha = 0.95
    horizon = 15000.0 if quick else 30000.0
    warmup = 0.1 * horizon
    acc = {(b, P): [] for P in Ps for b in betas}
    for s in range(seeds):
        a_downs, _ = simulate_address(
            GameParams(n=N, mu=MU, lam_a=LAM_A, horizon=horizon), seed=70_000 + s)
        for P in Ps:
            kmax_p = max(1, round(KMAX / P))
            for b in betas:
                prov_downs = [
                    simulate_provider(1.0 / P, b / P, kmax_p, horizon, warmup,
                                      seed=int(7e6 + s * 1000 + P * 311 + b * 101 + j))
                    for j in range(P)]
                dom_down = intersect(prov_downs)   # down iff ALL providers empty
                alld = _merge(list(a_downs) + list(dom_down))
                acc[(b, P)].append(
                    interval_up_probability(alld, warmup, horizon, 5.0))
    out = {"betas": betas, "Ps": Ps, "alpha": alpha, "kmax": KMAX, "curves": {}}
    for P in Ps:
        iv = [float(np.mean(acc[(b, P)])) for b in betas]
        bstar = _beta_star(betas, iv, alpha)
        out["curves"][str(P)] = {"interval": iv, "beta_star_interval": bstar}
    return out


def exp_discovery_robustness(seeds, quick):
    """E10: robustness of the frontier to the discovery model, and the
    diversification law A_P = 1 - q^P."""
    betas = list(np.round(np.linspace(0.2, 2.0, 16 if quick else 28), 4))
    alpha = 0.95
    horizon = 15000.0 if quick else 30000.0
    warmup = 0.1 * horizon
    accC = {b: [] for b in betas}
    accP = {b: [] for b in betas}
    for s in range(seeds):
        a_downs, _ = simulate_address(
            GameParams(n=N, mu=MU, lam_a=LAM_A, horizon=horizon), seed=80_000 + s)
        for b in betas:
            pc = GameParams(n=N, mu=MU, lam_a=LAM_A, lam_intro=1.0, lam_disc=b,
                            kmax=KMAX, horizon=horizon)
            dC, _pzC, _mkC = simulate_domain(pc, seed=int(8e6 + s * 1000 + b * 101))
            accC[b].append(interval_up_probability(
                _merge(list(a_downs) + list(dC)), warmup, horizon, 5.0))
            delta = b / KMAX                       # per-unit rate, matched at full pool
            rng = np.random.default_rng(int(8.5e6 + s * 1000 + b * 101))
            dP, _pzP, _ = _simulate_birth_death(
                birth_fn=lambda k: 1.0 if k < KMAX else 0.0,
                death_fn=lambda k, _d=delta: _d * k,
                x0=KMAX, hi=KMAX, horizon=horizon, warmup=warmup, rng=rng)
            accP[b].append(interval_up_probability(
                _merge(list(a_downs) + list(dP)), warmup, horizon, 5.0))
    const_iv = [float(np.mean(accC[b])) for b in betas]
    pername_iv = [float(np.mean(accP[b])) for b in betas]

    # Part B: diversification law at a fixed (stressed) beta
    beta_div = 1.0
    Ps = [1, 2, 3, 4, 6, 8]
    sim_avail, law_avail, qs = [], [], []
    measured = horizon - warmup
    for P in Ps:
        kmax_p = max(1, round(KMAX / P))
        sys_down, q_list = [], []
        for s in range(seeds):
            provs = [simulate_provider(1.0 / P, beta_div / P, kmax_p, horizon,
                                       warmup, seed=int(9e6 + s * 1000 + P * 311 + j * 101))
                     for j in range(P)]
            for pr in provs:
                q_list.append(sum(e - st for st, e in pr) / measured)
            alldown = intersect(provs)             # system down iff ALL providers empty
            sys_down.append(sum(e - st for st, e in alldown) / measured)
        q = float(np.mean(q_list))
        qs.append(q)
        sim_avail.append(1.0 - float(np.mean(sys_down)))
        law_avail.append(1.0 - q ** P)
    return {
        "betas": betas, "alpha": alpha, "kmax": KMAX,
        "const_interval": const_iv, "pername_interval": pername_iv,
        "beta_star_const": _beta_star(betas, const_iv, alpha),
        "beta_star_pername": _beta_star(betas, pername_iv, alpha),
        "div_beta": beta_div, "Ps": Ps, "q_per_provider": qs,
        "sim_avail": sim_avail, "law_avail": law_avail,
    }


EXPERIMENTS = {
    "E1": exp_ip_geometric,
    "E2": exp_phase_transition,
    "E3": exp_mu_heatmap,
    "E4": exp_beta_star_grid,
    "E5": exp_domain_economy,
    "E6": exp_session_length,
    "E7": exp_bursty_burns,
    "E8": exp_budget_allocation,
    "E9": exp_multiprovider,
    "E10": exp_discovery_robustness,
}


# =========================================================================== #
#  Figure renderers  (one function per paper figure; numbered 1-8)
# =========================================================================== #
def figure_1(R, path):
    """Address blocking is a losing strategy (E1)."""
    d = R["E1"]
    ns = d["ns"]
    fig, ax = plt.subplots(figsize=(3.4, 2.55))
    for i, ratio in enumerate(d["ratios"]):
        c = d["curves"][str(ratio)]
        ax.semilogy(ns, c["theory"], "-", color=COL[i], zorder=3,
                    label=fr"$\mu/\lambda_a={ratio:g}$")
        ax.semilogy(ns, c["sim"], "o", color=COL[i], ms=4, zorder=4,
                    **_open_marker(COL[i]))
    ax.set_xlabel("endpoints $n$")
    ax.set_ylabel(r"address-denial probability $P_{\mathrm{deny}}^{\mathrm{ip}}$")
    ax.set_ylim(1e-6, 1.5)
    ax.set_xlim(min(ns), max(ns))
    ax.text(0.97, 0.94, "lines: theory    markers: simulation",
            transform=ax.transAxes, fontsize=6.8, style="italic",
            ha="right", va="top", color="#444444")
    tidy(ax)
    toplegend(ax, ncol=4)
    _save(fig, path)


def figure_2(R, path):
    """The sustainability frontier / phase transition (E2)."""
    d = R["E2"]
    betas = np.array(d["betas"])
    alpha = d["alpha"]
    fig, ax = plt.subplots(figsize=(3.45, 2.7))
    ax.axvspan(1.0, betas.max(), color="#D55E00", alpha=0.05, zorder=0)
    for i, kmax in enumerate(d["kmaxes"]):
        c = d["curves"][str(kmax)]
        iv = np.array(c["interval"])
        std = np.array(c["interval_std"])
        ax.fill_between(betas, iv - std, iv + std, color=COL[i], alpha=0.13,
                        lw=0, zorder=2)
        ax.plot(betas, iv, "-", color=COL[i], zorder=3,
                label=fr"$k_{{\max}}={kmax}$")
    ax.axhline(alpha, ls=":", **REF)
    ax.axvline(1.0, **SEP)
    ax.text(1.03, 0.10, r"$\beta=1$", fontsize=7.5, color="#555555",
            rotation=90, va="bottom")
    ax.text(betas.max() - 0.02, alpha + 0.015, fr"$\alpha={alpha}$",
            fontsize=7.5, color="#555555", ha="right", va="bottom")
    ax.set_xlabel(r"domain burn rate $\beta=\lambda_{\mathrm{disc}}/\lambda_{\mathrm{intro}}$")
    ax.set_ylabel(r"$(\alpha,T)$-availability")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(betas.min(), betas.max())
    tidy(ax)
    toplegend(ax, ncol=len(d["kmaxes"]))
    _save(fig, path)


def figure_3(R, path):
    """Rotation speed is not the lever (E3)."""
    d = R["E3"]
    betas = np.array(d["betas"])
    ratios = np.array(d["ratios"])
    Z = np.array(d["time_avg"])  # rows: ratios, cols: betas
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    im = ax.pcolormesh(betas, ratios, Z, shading="gouraud",
                       cmap="viridis", vmin=0, vmax=1, rasterized=True)
    cs = ax.contour(betas, ratios, Z, levels=[0.95], colors="white",
                    linewidths=1.5, linestyles="--")
    cl = ax.clabel(cs, fmt={0.95: r"$0.95$"}, fontsize=7)
    for t in cl:
        t.set_bbox(dark_halo())
    ax.axvline(1.0, color="white", ls=":", lw=1.1, alpha=0.75)
    ax.set_yscale("log")
    ax.set_xlabel(r"domain burn rate $\beta$")
    ax.set_ylabel(r"rotation speed $\mu/\lambda_a$")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("time-average availability", fontsize=8)
    cb.outline.set_linewidth(0.6)
    ax.annotate("faster rotation\ndoes not cross\nthe frontier",
                xy=(1.0, ratios.max() * 0.6), xytext=(1.2, ratios.max() * 0.5),
                fontsize=6.8, color="white", bbox=dark_halo(),
                arrowprops=dict(arrowstyle="->", color="white", lw=0.9))
    heatmap_frame(ax)
    _save(fig, path)


def _panel_session_curves(ax, d):
    betas = np.array(d["betas"])
    Ts = d.get("Ts_display", [1.0, 5.0, 20.0])
    for i, T in enumerate(Ts):
        ax.plot(betas, d["curves"][str(T)], "-", color=COL[i % len(COL)],
                zorder=3, label=fr"$T={T:g}$")
    ax.axhline(0.95, ls=":", **REF)
    ax.set_xlabel(r"burn rate $\beta$")
    ax.set_ylabel(r"$(\alpha,T)$-avail.")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(betas.min(), betas.max())
    tidy(ax)
    complegend(ax, ncol=len(Ts))


def _panel_session_frontier(ax, d):
    Ts = d.get("Ts_frontier", d["Ts"])
    for i, a in enumerate(d["alphas"]):
        pts = [(T, d["beta_star"][str(a)][str(T)]) for T in Ts]
        xs = [t for t, y in pts if y is not None]
        ys = [y for _, y in pts if y is not None]
        ax.plot(xs, ys, "-o", color=COL[i], ms=3.2, zorder=3,
                label=fr"$\alpha={a}$", **_open_marker(COL[i]))
    ax.set_xscale("log")
    ax.set_xlabel(r"session length $T$")
    ax.set_ylabel(r"frontier $\beta^\star$")
    tidy(ax)
    complegend(ax, ncol=len(d["alphas"]))


def figure_4(R, path):
    """Longer sessions tighten the interval frontier (E6): (a) curves, (b) frontier."""
    d = R["E6"]
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.7))
    _panel_session_curves(axes[0], d)
    _panel_session_frontier(axes[1], d)
    _panel_tag(axes[0], "(a)")
    _panel_tag(axes[1], "(b)")
    fig.subplots_adjust(wspace=0.42)
    _save(fig, path)


def _panel_bursty(ax, d):
    betas = np.array(d["betas"])
    for i, bb in enumerate(d["batches"]):
        c = d["curves"][str(bb)]
        ax.plot(betas, c["interval"], "-", color=COL[i % len(COL)], zorder=3,
                label=fr"$b={bb}$")
    ax.axhline(d["alpha"], ls=":", **REF)
    ax.set_xlabel(r"$\beta$ (fixed mean)")
    ax.set_ylabel(r"$(\alpha,T)$-avail.")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(betas.min(), betas.max())
    tidy(ax)
    complegend(ax, ncol=len(d["batches"]), fs=5.8)


def _panel_multiprovider(ax, d):
    betas = np.array(d["betas"])
    for i, P in enumerate(d["Ps"]):
        c = d["curves"][str(P)]
        ax.plot(betas, c["interval"], "-", color=COL[i % len(COL)], zorder=3,
                label=fr"$P={P}$")
    ax.axhline(d["alpha"], ls=":", **REF)
    ax.axvline(1.0, **SEP)
    ax.set_xlabel(r"$\beta$ (prov.-corr.)")
    ax.set_ylabel(r"$(\alpha,T)$-avail.")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(betas.min(), betas.max())
    tidy(ax)
    complegend(ax, ncol=len(d["Ps"]), fs=5.8)


def _panel_discovery(ax, d):
    betas = np.array(d["betas"])
    ax.plot(betas, d["const_interval"], "-", color=COL[1], label="constant")
    ax.plot(betas, d["pername_interval"], "--", color=COL[0], label="per-unit")
    ax.axhline(d["alpha"], ls=":", **REF)
    ax.axvline(1.0, **SEP)
    ax.set_xlabel(r"burn rate $\beta$")
    ax.set_ylabel(r"$(\alpha,T)$-avail.")
    ax.set_ylim(0, 1.04)
    ax.set_xlim(betas.min(), betas.max())
    tidy(ax)
    complegend(ax, ncol=2)


def _panel_divlaw(ax, d):
    Ps = np.array(d["Ps"])
    ax.plot(Ps, d["law_avail"], "-", color=COL[2], lw=1.7, zorder=2,
            label=r"$1-q^{P}$")
    ax.plot(Ps, d["sim_avail"], "o", ms=4.5, zorder=3, label="sim",
            **_open_marker(COL[2]))
    ax.set_xlabel(r"providers $P$ ($\beta{=}1$)")
    ax.set_ylabel("availability")
    ax.set_ylim(0, 1.04)
    ax.set_xlim(Ps.min() - 0.3, Ps.max() + 0.3)
    tidy(ax)
    complegend(ax, ncol=2)


def figure_5(R, path):
    """Robustness analyses (E7, E9, E10): (a) bursty, (b) diversification,
    (c) discovery model, (d) diversification law."""
    fig, axes = plt.subplots(1, 4, figsize=(8.6, 2.5))
    _panel_bursty(axes[0], R["E7"])
    _panel_multiprovider(axes[1], R["E9"])
    _panel_discovery(axes[2], R["E10"])
    _panel_divlaw(axes[3], R["E10"])
    for ax, tag in zip(axes, ["(a)", "(b)", "(c)", "(d)"]):
        _panel_tag(ax, tag)
    fig.subplots_adjust(wspace=0.5)
    _save(fig, path)


def figure_6(R, path):
    """Closed-form time-average frontier beta*_avg over (n, kmax) per censor (E4)."""
    d = R["E4"]
    ns = d["ns"]
    kmaxes = d["kmaxes"]
    censors = list(d["censors"].keys())
    fig, axes = plt.subplots(1, len(censors), figsize=(7.0, 2.5), sharey=True)
    if len(censors) == 1:
        axes = [axes]
    vmin, vmax = 0.0, 1.05
    for ax, key in zip(axes, censors):
        grid = np.array([[np.nan if v is None else v for v in row]
                         for row in d["censors"][key]["beta_star"]])
        im = ax.imshow(grid, origin="lower", aspect="auto", cmap="magma",
                       vmin=vmin, vmax=vmax, rasterized=True)
        ax.set_xticks(range(len(kmaxes)))
        ax.set_xticklabels(kmaxes)
        ax.set_yticks(range(len(ns)))
        ax.set_yticklabels(ns)
        ax.set_xticks(np.arange(-0.5, len(kmaxes), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(ns), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.6)
        ax.tick_params(which="minor", length=0)
        ax.set_xlabel(r"buffer $k_{\max}$")
        ax.set_title(d["censors"][key]["label"], fontsize=8.5, pad=4)
        for i in range(len(ns)):
            for j in range(len(kmaxes)):
                if not np.isnan(grid[i, j]):
                    ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center",
                            fontsize=6.2, color=contrast_color(grid[i, j], vmin, vmax))
        for s in ax.spines.values():
            s.set_visible(True); s.set_linewidth(0.8); s.set_edgecolor("#444444")
    axes[0].set_ylabel(r"endpoints $n$")
    cb = fig.colorbar(im, ax=axes, pad=0.015, fraction=0.045)
    cb.set_label(r"time-average frontier $\beta^\star_{\mathrm{avg}}$", fontsize=8)
    cb.outline.set_linewidth(0.6)
    _save(fig, path)


def figure_7(R, path):
    """The censor's optimal budget split (E8)."""
    d = R["E8"]
    fracs = np.array(d["fracs"])
    lstyles = ["-", "-", (0, (1, 4)), (0, (1, 1.4))]
    marks = ["o", "s", "^", "D"]
    fig, ax = plt.subplots(figsize=(3.45, 2.7))
    for i, n in enumerate(d["ns"]):
        c = d["curves"][str(n)]
        ax.plot(fracs, c["interval"], color=COL[i % len(COL)],
                linestyle=lstyles[i % len(lstyles)], marker=marks[i % len(marks)],
                markevery=3, ms=4, zorder=3, label=fr"$n={n}$",
                **_open_marker(COL[i % len(COL)]))
    ax.axvline(1.0, **SEP)
    ax.text(0.965, 0.6, "all budget to domains", transform=ax.transAxes,
            fontsize=6.8, color="#555555", rotation=90, ha="center", va="center")
    ax.set_xlabel(r"censor budget fraction to domains $f$")
    ax.set_ylabel(r"$(\alpha,T)$-availability")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(fracs.min(), fracs.max())
    tidy(ax)
    toplegend(ax, ncol=len(d["ns"]))
    _save(fig, path)


def figure_8(R, path):
    """The domain-economy operating recipe (E5)."""
    d = R["E5"]
    burn = np.array(d["burn_per_day"])
    req = np.array(d["required_intro_per_day"])
    bstar = d["beta_star_interval"]
    fig, ax = plt.subplots(figsize=(3.45, 2.6))
    ax.fill_between(burn, req, burn, color=COL[2], alpha=0.12, lw=0, zorder=1)
    ax.plot(burn, burn, "--", color="#777777", lw=1.1, zorder=2,
            label=r"break-even ($\beta=1$)")
    ax.plot(burn, req, "-o", color=COL[0], ms=4, zorder=4,
            label=fr"required ($\beta<\beta^\star={bstar:g}$)", **_open_marker(COL[0]))
    ax.set_xlabel("censor domain-block rate (units/day)")
    ax.set_ylabel("required fresh units/day")
    ax.set_xlim(burn.min(), burn.max())
    tidy(ax)
    toplegend(ax, ncol=2)
    ax2 = ax.twinx()
    ax2.plot(burn, np.array(d["daily_cost"]), ":", color=COL[1], lw=1.6, zorder=3)
    ax2.set_ylabel(fr"cost (\$/day @ \${d['cost_per_domain']:g}/unit)",
                   color=COL[1], fontsize=8)
    ax2.tick_params(axis="y", labelcolor=COL[1], which="both", direction="out")
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(COL[1])
    ax2.spines["right"].set_linewidth(0.9)
    ax2.grid(False)
    ax2.minorticks_on()
    _save(fig, path)


FIGURES = {
    1: figure_1, 2: figure_2, 3: figure_3, 4: figure_4,
    5: figure_5, 6: figure_6, 7: figure_7, 8: figure_8,
}


def _save(fig, path):
    fig.savefig(path)
    plt.close(fig)
    print(f"  -> wrote {os.path.relpath(path)}")


# =========================================================================== #
#  Tables  (one function per paper table; numbered 1-4; written as plain text)
# =========================================================================== #
def _table_text(title, header, rows, note=None, align=None):
    """Render a fixed-width text table with a rule under the header.

    align: per-column 'l'/'r' string; default left-aligns column 0 and
    right-aligns the rest (good for a label column followed by numbers).
    """
    cols = [header] + rows
    ncol = len(header)
    widths = [max(len(str(r[c])) for r in cols) for c in range(ncol)]
    if align is None:
        align = "l" + "r" * (ncol - 1)

    def fmt(r):
        cells = [str(r[c]).ljust(widths[c]) if align[c] == "l"
                 else str(r[c]).rjust(widths[c]) for c in range(ncol)]
        return "  ".join(cells).rstrip()

    rule = "-" * (sum(widths) + 2 * (ncol - 1))
    lines = [title, "=" * max(len(title), len(rule)), "", fmt(header), rule]
    lines += [fmt(r) for r in rows]
    if note:
        lines += ["", note]
    return "\n".join(lines) + "\n"


def table_1(R):
    """Adversary profiles (dimensionless, with rotation rate mu=3)."""
    header = ["Censor", "address disc. lam_a", "mu/lam_a", "collateral gamma"]
    order = ["gfw", "tspu", "iran"]
    rows = []
    for key in order:
        c = CENSORS[key]
        rows.append([c["label"], f"{c['lam_a']:.1f}",
                     f"{MU / c['lam_a']:.2f}", f"{c['gamma']:.2f}"])
    note = ("Table 1: Adversary profiles. Mechanisms fixed to documented GFW, "
            "TSPU, and\nIranian designs; the numbers are deliberately "
            "adversary-favorable so reported\nguarantees are conservative. "
            "Source: censor_models.py.")
    return _table_text("Table 1  -  Adversary profiles", header, rows, note)


def table_2(R, seeds, quick):
    """Closed-form law vs simulation (kmax=8, canonical config)."""
    betas = [0.4, 0.6, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0]
    horizon = 30000.0 if not quick else 15000.0
    cf, sa, si = [], [], []
    for b in betas:
        cf.append(theory.stationary_availability(b, N, LAM_A, MU, KMAX))
        p = GameParams(n=N, mu=MU, lam_a=LAM_A, lam_intro=1.0, lam_disc=b,
                       kmax=KMAX, horizon=horizon)
        m = run(p, seeds=seeds)
        sa.append(m["time_avg_avail"])
        si.append(m["interval_avail"])

    def f3(x):
        # match the paper's ".993" style (no leading zero), 1.00 for >= 0.9995
        if x >= 0.9995:
            return "1.00"
        return f"{x:.3f}"[1:] if x < 1 else f"{x:.3f}"

    header = ["beta"] + [f"{b:g}" for b in betas]
    rows = [
        ["closed form"] + [f3(v) for v in cf],
        ["sim. (avg)"] + [f3(v) for v in sa],
        ["sim. (intvl)"] + [f3(v) for v in si],
    ]
    note = ("Table 2: Closed-form availability law vs. simulation (kmax=8, "
            "canonical config\nn=8, mu/lam_a=3). Time-average availability "
            "matches the closed form; the\ninterval metric is the stricter, "
            "binding one. Regenerated from this run.")
    return _table_text("Table 2  -  Closed-form law vs. simulation", header, rows, note)


def _renewal_beta_star(alpha, T, kmax, lam_intro=1.0, lo=1e-3, hi=10.0, tol=1e-7):
    """Largest beta whose renewal interval-availability >= alpha.

    interval-avail(beta) = (1 - pi0) * exp(-pi0 * lam_intro * T), pi0 increasing
    in beta, so the RHS is monotone decreasing -> bisect.
    """
    def rhs(b):
        pi0 = theory.pool_empty_prob(b, kmax)
        return (1.0 - pi0) * np.exp(-pi0 * lam_intro * T)
    if rhs(lo) < alpha:
        return None
    if rhs(hi) >= alpha:
        return hi
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if rhs(mid) >= alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def table_3(R):
    """Interval frontier beta*(alpha=0.95, T): renewal approximation vs simulation."""
    alpha = 0.95
    Ts = [1, 5, 20]
    d = R["E6"]
    betas = d["betas"]
    approx, sim = [], []
    for T in Ts:
        approx.append(_renewal_beta_star(alpha, T, KMAX))
        curve = d["curves"][str(float(T))]
        sim.append(_beta_star(betas, curve, alpha))
    header = ["session length T"] + [str(T) for T in Ts]
    rows = [
        ["approximation (renewal)"] + [f"{v:.2f}" if v is not None else "--" for v in approx],
        ["simulation"] + [f"{v:.2f}" if v is not None else "--" for v in sim],
    ]
    note = ("Table 3: Interval frontier beta*(alpha=0.95, T). The renewal "
            "approximation\n  interval-avail = (1 - pi0) * exp(-pi0 * lam_intro * T)\n"
            "tracks the simulated frontier to within the sweep resolution "
            "(kmax=8, lam_intro=1).")
    return _table_text("Table 3  -  Interval frontier (renewal vs. simulation)",
                       header, rows, note)


def table_4(R):
    """Simulator transition rates (next-event / Gillespie)."""
    header = ["layer", "transition", "rate"]
    rows = [
        ["address", "c -> c-1  (block)", "lam_a * c"],
        ["address", "c -> c+1  (rotate/recover)", "mu * (n - c)"],
        ["domain", "K -> K+1  (mint),  K < kmax", "lam_intro"],
        ["domain", "K -> K-1  (burn),  K >= 1", "lam_disc"],
    ]
    note = ("Table 4: Simulator transition rates. The two layers are advanced by "
            "the next-event\n(Gillespie) method. Bursty burns replace the domain "
            "death by a batch of b removals\nat rate lam_disc/b, leaving the mean "
            "burn rate unchanged. Source: rotation_game.py.")
    return _table_text("Table 4  -  Simulator transition rates", header, rows,
                       note, align="lll")


# =========================================================================== #
#  Driver
# =========================================================================== #
def main():
    ap = argparse.ArgumentParser(
        description="Regenerate every paper figure (PDF) and table (TXT).")
    ap.add_argument("--quick", action="store_true",
                    help="smaller sweeps / shorter horizons for a fast pass")
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__),
                                                      "output"),
                    help="output directory (default: ./output)")
    ap.add_argument("--no-data", action="store_true",
                    help="do not write the raw per-experiment JSON")
    args = ap.parse_args()

    seeds = 12 if args.quick else 24
    use_style()
    os.makedirs(args.outdir, exist_ok=True)
    t_start = time.time()

    # ---- 1. run the full simulation suite ------------------------------- #
    print(f"[1/3] Running experiments ({'quick' if args.quick else 'full'}, "
          f"{seeds} seeds)")
    R = {}
    for key, fn in EXPERIMENTS.items():
        t0 = time.time()
        print(f"  [{key}] {fn.__name__} ...", flush=True)
        R[key] = fn(seeds, args.quick)
        R[key]["_meta"] = {"seeds": seeds, "quick": args.quick,
                           "runtime_s": round(time.time() - t0, 1)}
        print(f"      done in {time.time() - t0:.1f}s", flush=True)

    if not args.no_data:
        data_dir = os.path.join(args.outdir, "data")
        os.makedirs(data_dir, exist_ok=True)
        for key, obj in R.items():
            with open(os.path.join(data_dir, f"{key}.json"), "w") as f:
                json.dump(obj, f, indent=2)
        print(f"  -> raw data written to {os.path.relpath(data_dir)}/")

    # ---- 2. render figures (numbered as in the paper) ------------------- #
    print("[2/3] Rendering figures")
    for num, fn in FIGURES.items():
        fn(R, os.path.join(args.outdir, f"figure_{num}.pdf"))

    # ---- 3. write tables (numbered as in the paper) --------------------- #
    print("[3/3] Writing tables")
    tables = {
        1: table_1(R),
        2: table_2(R, seeds, args.quick),
        3: table_3(R),
        4: table_4(R),
    }
    for num, text in tables.items():
        path = os.path.join(args.outdir, f"table_{num}.txt")
        with open(path, "w") as f:
            f.write(text)
        print(f"  -> wrote {os.path.relpath(path)}")

    print(f"\nAll artifacts in {os.path.relpath(args.outdir)}/  "
          f"(figure_1-8.pdf, table_1-4.txt)  in {time.time() - t_start:.1f}s.")


if __name__ == "__main__":
    main()
