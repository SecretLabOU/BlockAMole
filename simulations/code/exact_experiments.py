"""
exact_experiments.py -- exact-CTMC experiments R1-R13 and draft figures.

All quantities are computed exactly for the Markov model (see exact.py) unless
marked "MC", in which case an independent unit-level Monte Carlo implementation
(written separately from the exact chains) cross-checks the chain.

  R1  exact_validation        exact CTMC vs the event-driven simulations E1-E10
  R2  frontiers               beta*_avg and exact interval beta*(alpha,T) vs kmax
  R3  budget_split            censor budget split (aggregate model): corners,
                              corner criterion, star-shape argument
  R4  strategic_censor        strategic-timing censor (batch / strike) + reserve
  R5  diversification         pooled diversification vs single pool vs the
                              idle-clock model (E9)
  R6  heavy_tail_discovery    p = E[exp(-mu D)] for mean-1 discovery laws
  R7  sync_discovery          synchronized (sweep) address discovery
  R8  mint_exposure           mint-time exposure (pre-emptive burns)
  R9  range_blocking          range-blocked provider address space (crisis)
  R10 perunit_normalization   per-unit discovery under three normalizations
  R11 profiles                illustrative adversary profiles of
                              censor_models.py, exact beta*
  R13 rotation_speed          beta* vs mu/lam_a under both metrics
  FIG draft figures           ../figures_exact/fig_*.pdf

Canonical configuration: n=8, lam_intro=1, lam_a=1, mu=3, kmax=8, T=5,
alpha=0.95 (time unit 1/lam_intro).

Run:  python3 exact_experiments.py                 (everything, ~3-6 min)
      python3 exact_experiments.py --only R2,R4,FIG
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import sys
import time

import numpy as np
import scipy
from scipy import stats
from scipy.optimize import minimize_scalar
from scipy.special import gamma as gamma_fn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import exact as ex                                            # noqa: E402
from rotation_game import interval_up_probability            # noqa: E402

RESULTS = os.path.join(HERE, "..", "results")
FIGDIR = os.path.join(HERE, "..", "figures_exact")
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(FIGDIR, exist_ok=True)

N, LAM_INTRO, LAM_A, MU, KMAX, T5, ALPHA = 8, 1.0, 1.0, 3.0, 8, 5.0, 0.95


# --------------------------------------------------------------------------- #
#  bookkeeping
# --------------------------------------------------------------------------- #
def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _clean(obj):
    """JSON-safe copy: numpy scalars -> python, NaN/inf -> None."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if np.isfinite(v) else None
    return obj


def _meta(t0, extra=None):
    m = {
        "runtime_s": round(time.time() - t0, 2),
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "code_sha256": {
            "exact.py": _sha256(os.path.join(HERE, "exact.py")),
            "exact_experiments.py": _sha256(os.path.abspath(__file__)),
        },
        "canonical": dict(n=N, lam_intro=LAM_INTRO, lam_a=LAM_A, mu=MU,
                          kmax=KMAX, T=T5, alpha=ALPHA),
        "method": "exact CTMC (stationary law + pi_U expm(Q_UU T) 1); "
                  "MC = independent unit-level Monte Carlo cross-check",
    }
    if extra:
        m.update(extra)
    return m


def _save(name, obj):
    path = os.path.join(RESULTS, name)
    with open(path, "w") as f:
        json.dump(_clean(obj), f, indent=1)
    print(f"  -> wrote {os.path.relpath(path)}")


def _addr(T, n=N, lam_a=LAM_A, mu=MU):
    return ex.addr_window(n, lam_a, mu, T)


def _bstar(fn, alpha=ALPHA, **kw):
    v, st = ex.beta_star(fn, alpha, **kw)
    return v, st


def _grid_floor(betas, vals, alpha):
    """Largest grid beta whose value is >= alpha (the grid-floor rule of
    run_experiments.py)."""
    out = None
    for b, v in zip(betas, vals):
        if v >= alpha:
            out = b
    return out


MC_SEEDS = 16          # independent seeds per Monte Carlo cross-check
MC_HORIZON = 1.0e5     # simulated time per seed (units of 1/lam_intro)


def _par_starmap(fn, arglist):
    """fn(*args) for every args, in parallel (fork); results in input order.
    Every call carries its own fixed seed, so results do not depend on the
    process scheduling."""
    import multiprocessing as mp
    nproc = max(1, min(len(arglist), os.cpu_count() or 1))
    if nproc == 1:
        return [fn(*a) for a in arglist]
    with mp.get_context("fork").Pool(nproc) as pool:
        return pool.starmap(fn, arglist)


def _mc_summary(sims, exact_window, exact_timeavg):
    """Mean, standard error across seeds and z-scores vs the exact values."""
    iv = np.array([x[0] for x in sims])
    ta = np.array([x[1] for x in sims])
    m = len(sims)
    sw = iv.std(ddof=1) / np.sqrt(m)
    sa = ta.std(ddof=1) / np.sqrt(m)
    return {"exact_window": exact_window, "mc_window": float(iv.mean()),
            "mc_window_se": float(sw),
            "z_window": float((iv.mean() - exact_window) / sw) if sw > 0 else None,
            "exact_timeavg": exact_timeavg, "mc_timeavg": float(ta.mean()),
            "mc_timeavg_se": float(sa),
            "z_timeavg": float((ta.mean() - exact_timeavg) / sa) if sa > 0 else None,
            "mc_seeds": m, "mc_horizon": MC_HORIZON}


# =========================================================================== #
#  R1  exact validation of the event-driven simulation results
# =========================================================================== #
def r1_validation():
    res = {"inputs": {}, "summary": {}}

    def load(name):
        path = os.path.join(RESULTS, name)
        res["inputs"][name] = {"sha256": _sha256(path),
                               "bytes": os.path.getsize(path)}
        with open(path) as f:
            return json.load(f)

    def stats_of(sim, exact_, se=None):
        sim, exact_ = np.asarray(sim, float), np.asarray(exact_, float)
        d = sim - exact_
        out = {"n_points": int(d.size),
               "max_abs_diff": float(np.max(np.abs(d))),
               "mean_abs_diff": float(np.mean(np.abs(d))),
               "mean_signed_diff": float(np.mean(d))}
        if se is not None:
            se = np.asarray(se, float)
            ok = se > 0
            z = d[ok] / se[ok]
            out.update({"max_abs_z": float(np.max(np.abs(z))) if z.size else None,
                        "frac_within_2se": float(np.mean(np.abs(z) <= 2)) if z.size else None,
                        "frac_within_3se": float(np.mean(np.abs(z) <= 3)) if z.size else None,
                        "n_points_with_se": int(ok.sum())})
        return out

    # ---- E1 address layer -------------------------------------------------
    d = load("E1_ip_geometric.json")
    e1 = {}
    for ratio in d["ratios"]:
        c = d["curves"][str(ratio)]
        exact_ = [(1.0 / (1.0 + ratio)) ** n for n in d["ns"]]
        sim = c["sim"]
        rel = [(s - e) / e for s, e in zip(sim, exact_)]
        e1[str(ratio)] = {"ns": d["ns"], "exact": exact_, "sim": sim,
                          "rel_diff": rel}
    allsim = sum((e1[k]["sim"] for k in e1), [])
    allex = sum((e1[k]["exact"] for k in e1), [])
    rel = np.array(sum((e1[k]["rel_diff"] for k in e1), []))
    big = np.array(allex) >= 1e-3
    res["E1"] = {"curves": e1, "stats": stats_of(allsim, allex),
                 "max_abs_rel_diff_exact_ge_1e-3": float(np.max(np.abs(rel[big]))),
                 "max_abs_rel_diff_exact_lt_1e-3": float(np.max(np.abs(rel[~big]))),
                 "note": "exact = (lam_a/(lam_a+mu))^n, lam_a=1, mu=ratio"}

    # ---- E2 phase transition ---------------------------------------------
    d = load("E2_phase_transition.json")
    seeds = d["_meta"]["seeds"]
    a5 = _addr(5.0)
    e2 = {}
    sims, exs, ses, simta, exta = [], [], [], [], []
    for k in d["kmaxes"]:
        c = d["curves"][str(k)]
        b = d["betas"]
        ex_iv = [ex.name_window_constant(x, k, 5.0) * a5 for x in b]
        ex_ta = [ex.timeavg_availability(x, k, N, LAM_A, MU) for x in b]
        se = [s / np.sqrt(seeds) for s in c["interval_std"]]
        root, _ = _bstar(lambda x, k=k: ex.name_window_constant(x, k, 5.0) * a5)
        e2[str(k)] = {"exact_interval": ex_iv, "exact_timeavg": ex_ta,
                      "stats_interval": stats_of(c["interval"], ex_iv, se),
                      "stats_timeavg": stats_of(c["time_avg"], ex_ta),
                      "beta_star_grid_sim": c["beta_star_interval"],
                      "beta_star_grid_exact": _grid_floor(b, ex_iv, ALPHA),
                      "beta_star_exact_root": root}
        sims += c["interval"]; exs += ex_iv; ses += se
        simta += c["time_avg"]; exta += ex_ta
    res["E2"] = {"per_kmax": e2, "stats_interval": stats_of(sims, exs, ses),
                 "stats_timeavg": stats_of(simta, exta), "seeds": seeds}

    # ---- E3 mu heatmap ------------------------------------------------------
    d = load("E3_mu_heatmap.json")
    b, ratios = d["betas"], d["ratios"]
    ex_ta = [[ex.timeavg_availability(x, d["kmax"], d["n"], 1.0, r) for x in b]
             for r in ratios]
    nw = np.array([ex.name_window_constant(x, d["kmax"], 5.0) for x in b])
    ex_iv = [list(nw * ex.addr_window(d["n"], 1.0, r, 5.0)) for r in ratios]
    res["E3"] = {"stats_timeavg": stats_of(np.ravel(d["time_avg"]), np.ravel(ex_ta)),
                 "stats_interval": stats_of(np.ravel(d["interval"]), np.ravel(ex_iv)),
                 "exact_interval": ex_iv, "exact_timeavg": ex_ta}

    # ---- E4 closed-form grid (bisection in theory.py) --------------------
    d = load("E4_beta_star_grid.json")
    from censor_models import CENSORS
    diffs = []
    for key, c in d["censors"].items():
        la = CENSORS[key]["lam_a"]
        for i, n in enumerate(d["ns"]):
            for j, k in enumerate(d["kmaxes"]):
                v, st = ex.beta_star_avg(d["alpha"], k, n, la, MU)
                old = c["beta_star"][i][j]
                if v is None or old is None:
                    if not (v is None and old is None):
                        diffs.append(np.inf)
                else:
                    diffs.append(abs(v - old))
    res["E4"] = {"max_abs_diff_beta_star_avg": float(np.max(diffs)),
                 "n_cells": len(diffs)}

    # ---- E5 domain economy -------------------------------------------------
    d = load("E5_domain_economy.json")
    ex_iv = [ex.name_window_constant(x, d["kmax"], 5.0) * a5 for x in d["betas"]]
    res["E5"] = {"stats_interval": stats_of(d["interval"], ex_iv),
                 "exact_interval": ex_iv,
                 "beta_star_grid_sim": d["beta_star_interval"],
                 "beta_star_grid_exact": _grid_floor(d["betas"], ex_iv, ALPHA)}

    # ---- E6 session length ---------------------------------------------------
    d = load("E6_session_length.json")
    Ts = np.array(d["Ts"], float)
    aT = ex.addr_window(N, LAM_A, MU, Ts)
    sims, exs = [], []
    per_T = {}
    exact_curves = {}
    for ti, Tv in enumerate(d["Ts"]):
        exact_curves[str(Tv)] = []
    for bi, x in enumerate(d["betas"]):
        w = ex.name_window_constant(x, d["kmax"], Ts) * aT
        for ti, Tv in enumerate(d["Ts"]):
            exact_curves[str(Tv)].append(float(w[ti]))
    for Tv in d["Ts"]:
        s, e = d["curves"][str(Tv)], exact_curves[str(Tv)]
        per_T[str(Tv)] = stats_of(s, e)["max_abs_diff"]
        sims += s; exs += e
    bs_cmp = {}
    mism = 0
    for a in d["alphas"]:
        bs_cmp[str(a)] = {}
        for Tv in d["Ts_frontier"]:
            root, _ = _bstar(lambda x, Tv=Tv: ex.name_window_constant(
                x, d["kmax"], Tv) * _addr(Tv), alpha=a)
            gf_ex = _grid_floor(d["betas"], exact_curves[str(Tv)], a)
            gf_sim = d["beta_star"][str(a)][str(Tv)]
            mism += int(gf_ex != gf_sim)
            bs_cmp[str(a)][str(Tv)] = {"sim_grid": gf_sim, "exact_grid": gf_ex,
                                       "exact_root": root}
    res["E6"] = {"stats_interval": stats_of(sims, exs),
                 "max_abs_diff_per_T": per_T, "beta_star": bs_cmp,
                 "n_grid_floor_mismatches": mism,
                 "n_grid_floor_comparisons": len(d["alphas"]) * len(d["Ts_frontier"])}

    # ---- E7 bursty burns -------------------------------------------------------
    d = load("E7_bursty_burns.json")
    e7 = {}
    sims, exs = [], []
    for bb in d["batches"]:
        ch = ex.batch_name_chain(d["kmax"], bb)
        ex_iv = [ch.window(5.0, intro=1.0, disc=x) * a5 for x in d["betas"]]
        root, st = _bstar(lambda x, ch=ch: ch.window(5.0, intro=1.0, disc=x) * a5)
        c = d["curves"][str(bb)]
        e7[str(bb)] = {"exact_interval": ex_iv,
                       "stats_interval": stats_of(c["interval"], ex_iv),
                       "beta_star_grid_sim": c["beta_star_interval"],
                       "beta_star_grid_exact": _grid_floor(d["betas"], ex_iv, ALPHA),
                       "beta_star_exact_root": root, "root_status": st}
        sims += c["interval"]; exs += ex_iv
    res["E7"] = {"per_b": e7, "stats_interval": stats_of(sims, exs)}

    # ---- E8 budget (aggregate model, per-endpoint lam_a=(1-f)B/n) ----------
    d = load("E8_budget_allocation.json")
    e8 = {}
    sims, exs = [], []
    B = d["B"]
    for n in d["ns"]:
        ex_iv = []
        for f in d["fracs"]:
            la = max(1e-6, (1.0 - f) * B / n)
            ex_iv.append(ex.name_window_constant(f * B, d["kmax"], 5.0)
                         * ex.addr_window(n, la, d["mu"], 5.0))
        c = d["curves"][str(n)]
        e8[str(n)] = {"exact_interval": ex_iv,
                      "stats_interval": stats_of(c["interval"], ex_iv)}
        sims += c["interval"]; exs += ex_iv
    res["E8"] = {"per_n": e8, "stats_interval": stats_of(sims, exs)}

    # ---- E9 multiprovider (idle-clock model) ---------------------------------
    d = load("E9_multiprovider.json")
    e9 = {}
    sims, exs = [], []
    for P in d["Ps"]:
        kp = max(1, round(d["kmax"] / P))
        ch = ex.providers_chain(P, kp, "idle")
        ex_iv = [ch.window(5.0, intro=1.0, disc=x) * a5 for x in d["betas"]]
        root, st = _bstar(lambda x, ch=ch: ch.window(5.0, intro=1.0, disc=x) * a5)
        c = d["curves"][str(P)]
        e9[str(P)] = {"kp": kp, "exact_interval": ex_iv,
                      "stats_interval": stats_of(c["interval"], ex_iv),
                      "beta_star_grid_sim": c["beta_star_interval"],
                      "beta_star_exact_root": root}
        sims += c["interval"]; exs += ex_iv
    res["E9"] = {"per_P": e9, "stats_interval": stats_of(sims, exs)}

    # ---- E10 discovery robustness + diversification law -------------------
    d = load("E10_discovery_robustness.json")
    k = d["kmax"]
    ex_c = [ex.name_window_constant(x, k, 5.0) * a5 for x in d["betas"]]
    ex_p = [ex.name_window_perunit(x / k, k, 5.0) * a5 for x in d["betas"]]
    qb = d["div_beta"] / (1.0 + d["div_beta"])
    law = [1.0 - qb ** P for P in d["Ps"]]
    res["E10"] = {
        "stats_const": stats_of(d["const_interval"], ex_c),
        "stats_perunit": stats_of(d["pername_interval"], ex_p),
        "exact_const": ex_c, "exact_perunit": ex_p,
        "q_exact": qb, "q_sim": d["q_per_provider"],
        "stats_q": stats_of(d["q_per_provider"], [qb] * len(d["Ps"])),
        "stats_divlaw_avail": stats_of(d["sim_avail"], law),
        "exact_divlaw_avail": law,
        "beta_star_grid_sim": {"const": d["beta_star_const"],
                               "perunit": d["beta_star_pername"]},
        "beta_star_grid_exact": {"const": _grid_floor(d["betas"], ex_c, ALPHA),
                                 "perunit": _grid_floor(d["betas"], ex_p, ALPHA)},
    }
    res["summary"] = {
        "E1_max_abs_diff": res["E1"]["stats"]["max_abs_diff"],
        "E2_interval_max_abs_diff": res["E2"]["stats_interval"]["max_abs_diff"],
        "E2_interval_max_abs_z": res["E2"]["stats_interval"]["max_abs_z"],
        "E2_timeavg_max_abs_diff": res["E2"]["stats_timeavg"]["max_abs_diff"],
        "E3_interval_max_abs_diff": res["E3"]["stats_interval"]["max_abs_diff"],
        "E3_timeavg_max_abs_diff": res["E3"]["stats_timeavg"]["max_abs_diff"],
        "E4_max_abs_diff": res["E4"]["max_abs_diff_beta_star_avg"],
        "E5_interval_max_abs_diff": res["E5"]["stats_interval"]["max_abs_diff"],
        "E6_interval_max_abs_diff": res["E6"]["stats_interval"]["max_abs_diff"],
        "E7_interval_max_abs_diff": res["E7"]["stats_interval"]["max_abs_diff"],
        "E8_interval_max_abs_diff": res["E8"]["stats_interval"]["max_abs_diff"],
        "E9_interval_max_abs_diff": res["E9"]["stats_interval"]["max_abs_diff"],
        "E10_const_max_abs_diff": res["E10"]["stats_const"]["max_abs_diff"],
        "E10_perunit_max_abs_diff": res["E10"]["stats_perunit"]["max_abs_diff"],
        "E10_divlaw_max_abs_diff": res["E10"]["stats_divlaw_avail"]["max_abs_diff"],
    }
    return res


# =========================================================================== #
#  R2  frontiers
# =========================================================================== #
R2_KMAX = [2, 4, 8, 16, 32, 64, 128, 256]
R2_T = [1.0, 2.0, 5.0, 10.0, 20.0]
R2_ALPHA = [0.9, 0.95, 0.99]


def _min_kmax_above_one(alpha, T=None, ca=None):
    """Smallest integer kmax with frontier > 1, i.e. availability at beta=1
    strictly above alpha (availability is decreasing in beta). T=None ->
    time-average metric."""
    if T is None:
        val = lambda k: (1.0 - 1.0 / (k + 1.0)) * ca
    else:
        aT = _addr(T)
        val = lambda k: ex.name_window_constant(1.0, k, T) * aT
    lo, hi = 1, 2
    while val(hi) <= alpha:
        lo, hi = hi, hi * 2
        if hi > 1 << 20:
            return None, None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if val(mid) > alpha:
            hi = mid
        else:
            lo = mid
    mono = bool(val(hi - 1) <= alpha < val(hi) <= val(hi + 1))
    return hi, mono


def r2_frontiers():
    ca = ex.addr_timeavg(N, LAM_A, MU)
    aT = {T: _addr(T) for T in R2_T}
    rows, viol = [], []
    for a in R2_ALPHA:
        for k in R2_KMAX:
            bavg, st_avg = ex.beta_star_avg(a, k, N, LAM_A, MU)
            for T in R2_T:
                f = lambda b, k=k, T=T: ex.name_window_constant(b, k, T) * aT[T]
                bint, st = _bstar(f, alpha=a)
                single = ex.check_single_crossing(f, a, bint)
                chain = (bint <= bavg + 1e-12) and (bavg <= ca / a + 1e-12) \
                    and (ca / a <= 1.0 / a)
                if not chain:
                    viol.append((a, k, T))
                rows.append({"alpha": a, "kmax": k, "T": T,
                             "beta_star_interval": bint, "status": st,
                             "beta_star_avg": bavg, "ca_over_alpha": ca / a,
                             "one_over_alpha": 1.0 / a,
                             "single_crossing": single, "chain_ok": chain})
    # monotonicity in kmax
    mono_k = True
    for a in R2_ALPHA:
        for T in R2_T:
            seq = [r["beta_star_interval"] for r in rows
                   if r["alpha"] == a and r["T"] == T]
            mono_k &= all(x2 >= x1 for x1, x2 in zip(seq, seq[1:]))
    # smallest kmax with beta* > 1
    cross = {}
    for a in R2_ALPHA:
        kavg, mavg = _min_kmax_above_one(a, ca=ca)
        cross[str(a)] = {"time_average": kavg}
        for T in R2_T:
            kint, mono = _min_kmax_above_one(a, T=T)
            cross[str(a)][str(T)] = {"kmax": kint, "monotone_check": mono}
    # large-kmax limit of the interval frontier
    big = [512, 1024, 2048, 4096, 8192]
    limit = {}
    for a in R2_ALPHA:
        limit[str(a)] = {}
        for T in R2_T:
            vals = []
            for k in big:
                f = lambda b, k=k, T=T: ex.name_window_constant(b, k, T) * aT[T]
                vals.append(_bstar(f, alpha=a)[0])
            limit[str(a)][str(T)] = dict(zip(map(str, big), vals))
    # dense curves (figure b)
    kd = sorted(set(list(range(2, 65)) + list(range(68, 129, 4))
                    + list(range(144, 513, 16)) + [768, 1024, 1536, 2048,
                                                   3072, 4096]))
    dense = {"kmax": kd, "interval": {}, "avg": {}}
    for a in R2_ALPHA:
        dense["avg"][str(a)] = [ex.beta_star_avg(a, k, N, LAM_A, MU)[0] for k in kd]
        for T in (1.0, 5.0, 20.0):
            dense["interval"][f"{a}|{T}"] = [
                _bstar(lambda b, k=k, T=T: ex.name_window_constant(b, k, T)
                       * aT[T], alpha=a)[0] for k in kd]
    return {"config": dict(n=N, lam_a=LAM_A, mu=MU, lam_intro=LAM_INTRO),
            "address_window": {str(T): aT[T] for T in R2_T}, "c_a": ca,
            "table": rows, "chain_violations": viol,
            "all_chain_ok": len(viol) == 0,
            "all_single_crossing": all(r["single_crossing"] for r in rows),
            "interval_beta_star_nondecreasing_in_kmax": mono_k,
            "min_kmax_beta_star_above_1": cross,
            "large_kmax_interval_beta_star": limit, "dense": dense}


# =========================================================================== #
#  R3  censor budget split (aggregate model)
# =========================================================================== #
TOL = 1e-12   # absolute tolerance for "interior below corner" comparisons


def _budget_curves(B, n, k, fs, T=T5):
    """Name and address factors along the budget line, both metrics.
    lam_disc = f B, aggregate address rate Lambda_a = (1-f) B, per-endpoint
    lam_a = Lambda_a / n."""
    ys = fs * B
    lam_a = (1.0 - fs) * B / n
    N_avg = np.array([1.0 - ex.pi0_geometric(y, k) for y in ys])
    C_avg = np.array([ex.addr_timeavg(n, la, MU) for la in lam_a])
    N_int = np.array([ex.name_window_constant(y, k, T) for y in ys])
    C_int = np.array([ex.addr_window(n, la, MU, T) for la in lam_a])
    return {"timeavg": (N_avg, C_avg), "interval": (N_int, C_int)}


def _point(B, n, k, f, metric, T=T5):
    la = (1.0 - f) * B / n
    if metric == "timeavg":
        return (1.0 - ex.pi0_geometric(f * B, k)) * ex.addr_timeavg(n, la, MU)
    return ex.name_window_constant(f * B, k, T) * ex.addr_window(n, la, MU, T)


def _local_minima(vals, tol=TOL):
    """Interior grid points that are local minima by more than tol."""
    out = []
    for i in range(1, len(vals) - 1):
        if vals[i] < vals[i - 1] - tol and vals[i] <= vals[i + 1]:
            out.append(i)
    return out


def _chord_ok(fs, Nf, Cf, tol=TOL):
    """Chord (star-shape) premises on the grid: with U = -log N(fB) and
    V = -log C((1-f)B),  U(f) <= f U(1) + tol  and  V(f) <= (1-f) V(0) + tol.
    If both hold, U + V <= max(U(1), V(0)) + 2 tol, i.e. A(f) >= min corners."""
    with np.errstate(divide="ignore"):
        U = -np.log(Nf)
        V = -np.log(Cf)
    okU = np.all((U <= np.where(fs > 0, fs * U[-1], 0.0) + tol) | ~np.isfinite(U[-1]))
    okV = np.all((V <= np.where(fs < 1, (1 - fs) * V[0], 0.0) + tol) | ~np.isfinite(V[0]))
    return bool(okU), bool(okV)


def _star_limit(fun, ymax, npts=20001):
    """Largest y in (0, ymax] such that fun(t)/t is nondecreasing on (0, y]
    (checked on a fine grid)."""
    y = np.linspace(ymax / npts, ymax, npts)
    r = np.array([fun(t) for t in y]) / y
    dec = np.flatnonzero(np.diff(r) < -1e-14 * np.maximum(1.0, np.abs(r[:-1])))
    return float(ymax) if dec.size == 0 else float(y[dec[0]])


def _analyse_curve(fs, v, B, n, k, metric):
    i = int(np.argmin(v))
    corner_min = min(v[0], v[-1])
    interior_min = float(np.min(v[1:-1]))
    is_corner = interior_min >= corner_min - TOL
    refined = []
    for li in _local_minima(v):
        lo, hi = fs[max(li - 2, 0)], fs[min(li + 2, len(fs) - 1)]
        r = minimize_scalar(lambda f: _point(B, n, k, f, metric), bounds=(lo, hi),
                            method="bounded", options={"xatol": 1e-10})
        refined.append({"f": float(r.x), "value": float(r.fun),
                        "below_best_corner_by": float(corner_min - r.fun)})
    return {"A_f0": float(v[0]), "A_f1": float(v[-1]),
            "argmin_f": float(fs[i]) if not is_corner else (0.0 if v[0] <= v[-1] else 1.0),
            "min": float(min(np.min(v), corner_min)),
            "argmin_is_corner": bool(is_corner),
            "interior_min_minus_corner_min": float(interior_min - corner_min),
            "interior_local_minima": refined}


def r3_budget():
    Bs = [0.25, 0.5, 1.0, 1.5, 2.0]
    ns = [1, 2, 4, 8]
    ks = [8, 32]
    fs = np.linspace(0.0, 1.0, 401)
    # premises of the time-average corner theorem
    star = {}
    for k in ks:
        U = lambda y, k=k: -np.log1p(-ex.pi0_geometric(y, k))
        star[f"y_U(kmax={k})"] = _star_limit(U, 6.0)
    for n in ns:
        star[f"x_V(n={n})"] = float(n * (n - 1) * MU)   # analytic (0 for n=1)
    rows = []
    for B in Bs:
        for n in ns:
            for k in ks:
                cur = _budget_curves(B, n, k, fs)
                row = {"B": B, "n": n, "kmax": k}
                for metric in ("timeavg", "interval"):
                    Nf, Cf = cur[metric]
                    rec = _analyse_curve(fs, Nf * Cf, B, n, k, metric)
                    okU, okV = _chord_ok(fs, Nf, Cf)
                    rec["chord_premise_U_on_grid"] = okU
                    rec["chord_premise_V_on_grid"] = okV
                    row[metric] = rec
                crit = ex.pi0_geometric(B, k) >= (B / (B + n * MU)) ** n
                row["criterion_names_optimal_timeavg"] = bool(crit)
                row["criterion_matches_argmin_timeavg"] = bool(
                    crit == (row["timeavg"]["argmin_f"] == 1.0))
                crit_i = ex.name_window_constant(B, k, T5) <= ex.addr_window(n, B / n, MU, T5)
                row["criterion_names_optimal_interval"] = bool(crit_i)
                row["criterion_matches_argmin_interval"] = bool(
                    crit_i == (row["interval"]["argmin_f"] == 1.0))
                row["theorem_applies_timeavg"] = bool(
                    n >= 2 and B <= star[f"y_U(kmax={k})"] and B <= n * (n - 1) * MU)
                rows.append(row)
    # beyond the requested grid: where do interior optima appear?
    extra = []
    fsx = np.linspace(0, 1, 801)
    for n in (1, 2):
        for k in ks:
            for B in (2.5, 3.0, 3.5, 4.0, 6.0, 8.0, 12.0, 20.0, 40.0):
                cur = _budget_curves(B, n, k, fsx)
                for metric in ("timeavg", "interval"):
                    Nf, Cf = cur[metric]
                    rec = _analyse_curve(fsx, Nf * Cf, B, n, k, metric)
                    rec.update({"B": B, "n": n, "kmax": k, "metric": metric})
                    extra.append(rec)
    summ = {
        "n_configs": len(rows),
        "timeavg_all_corner": all(r["timeavg"]["argmin_is_corner"] for r in rows),
        "interval_all_corner": all(r["interval"]["argmin_is_corner"] for r in rows),
        "timeavg_any_interior_local_min": any(r["timeavg"]["interior_local_minima"] for r in rows),
        "interval_any_interior_local_min": any(r["interval"]["interior_local_minima"] for r in rows),
        "criterion_matches_all_timeavg": all(r["criterion_matches_argmin_timeavg"] for r in rows),
        "criterion_matches_all_interval": all(r["criterion_matches_argmin_interval"] for r in rows),
        "n_names_corner_timeavg": sum(r["timeavg"]["argmin_f"] == 1.0 for r in rows),
        "n_address_corner_timeavg": sum(r["timeavg"]["argmin_f"] == 0.0 for r in rows),
        "n_names_corner_interval": sum(r["interval"]["argmin_f"] == 1.0 for r in rows),
        "n_address_corner_interval": sum(r["interval"]["argmin_f"] == 0.0 for r in rows),
        "theorem_covers_timeavg": sum(r["theorem_applies_timeavg"] for r in rows),
        "chord_premises_hold_timeavg": sum(r["timeavg"]["chord_premise_U_on_grid"]
                                           and r["timeavg"]["chord_premise_V_on_grid"]
                                           for r in rows),
        "chord_premises_hold_interval": sum(r["interval"]["chord_premise_U_on_grid"]
                                            and r["interval"]["chord_premise_V_on_grid"]
                                            for r in rows),
        "beyond_grid_interior_cases": [
            {k2: e[k2] for k2 in ("metric", "n", "kmax", "B", "A_f0", "A_f1",
                                  "interior_min_minus_corner_min",
                                  "interior_local_minima")}
            for e in extra if not e["argmin_is_corner"]],
    }
    return {"grid": {"B_over_lam_intro": Bs, "n": ns, "kmax": ks,
                     "f_points": len(fs), "T": T5, "mu": MU, "tol": TOL},
            "model": "B = Lambda_a + lam_disc; per-endpoint lam_a = (1-f)B/n; "
                     "lam_disc = f B (lam_intro = 1)",
            "theorem": ("Let U(y) = -log(1 - pi0(y,kmax)) and V(x) = -log(1 - "
                        "(x/(x+n mu))^n). If U(y)/y is nondecreasing on (0,B] "
                        "and V(x)/x is nondecreasing on (0,B], then for every "
                        "f in [0,1]: U(fB) + V((1-f)B) <= f U(B) + (1-f) V(B) "
                        "<= max(U(B), V(B)), so A(f) = exp(-U-V) >= "
                        "min(A(0), A(1)): the censor's best split is a corner, "
                        "and names are optimal iff pi0(B,kmax) >= "
                        "(B/(B+n mu))^n. V(x)/x is nondecreasing iff "
                        "x <= n(n-1) mu (n >= 2; it fails for n = 1); "
                        "U(y)/y is nondecreasing up to y_U(kmax) (numeric)."),
            "star_shape_limits": star,
            "rows": rows, "beyond_grid": extra, "summary": summ}


# =========================================================================== #
#  R4  strategic timing censor and reserve
# =========================================================================== #
def _mc_strategic(kmax, beta, policy, j, r, horizon, seed, T=T5):
    """Independent unit-level simulation of the strategic censor model."""
    rng = np.random.default_rng(seed)
    active = []                  # discovered flags of active units
    reserve = 0
    t = 0.0
    warm = 0.1 * horizon
    downs = []
    dstart = 0.0                 # system starts empty (down)
    up_time = 0.0
    while t < horizon:
        und = [i for i, x in enumerate(active) if not x]
        r_mint = LAM_INTRO if len(active) + reserve < kmax else 0.0
        r_disc = beta * LAM_INTRO if und else 0.0
        R = r_mint + r_disc
        dt = rng.exponential(1.0 / R)
        t_next = min(t + dt, horizon)
        if active and t_next > warm:
            up_time += t_next - max(t, warm)
        t = t + dt
        if t >= horizon:
            break
        was_up = bool(active)
        if rng.random() * R < r_mint:
            if not active:
                active.append(False)
            elif reserve < r:
                reserve += 1
            else:
                active.append(False)
        else:
            active[und[rng.integers(len(und))]] = True
            D = sum(active)
            A = len(active)
            strike = {"poisson": True, "batch": D == j,
                      "batch_or_all": D == j or D == A,
                      "strike_all": D == A}[policy]
            if strike:
                active = [x for x in active if not x]
                if not active and reserve > 0:
                    active = [False] * reserve
                    reserve = 0
        is_up = bool(active)
        if was_up and not is_up:
            dstart = t
        elif (not was_up) and is_up:
            downs.append((dstart, t))
            dstart = None
    if not active and dstart is not None:
        downs.append((dstart, horizon))
    downs = [(max(s, 0.0), e) for s, e in downs if e > warm]
    iv = interval_up_probability(downs, warm, horizon, T)
    return iv, up_time / (horizon - warm)


def r4_strategic():
    a5 = _addr(T5)
    ca = ex.addr_timeavg(N, LAM_A, MU)
    out = {"policies": {}, "reserve": {}, "mc_check": []}
    for k in (8, 32):
        pols = [("poisson", None)] + [("batch", j) for j in (2, 4, 8, k) if j <= k] \
            + [("batch_or_all", j) for j in (2, 4, 8) if j < k] + [("strike_all", None)]
        pols = list(dict.fromkeys(pols))
        res = {}
        for pol, j in pols:
            ch = ex.strategic_chain(k, pol, j=j, r=0)
            fi = lambda b, ch=ch: ch.window(T5, intro=1.0, disc=b) * a5
            fa = lambda b, ch=ch: ch.timeavg(intro=1.0, disc=b) * ca
            bi, sti = _bstar(fi)
            ba, sta = _bstar(fa)
            blocked = lambda s, t: (s[0] + s[1]) - (t[0] + t[1])
            key = pol if j is None else f"{pol}_j{j}"
            res[key] = {"policy": pol, "j": j, "states": ch.N,
                        "beta_star_interval": bi, "status_interval": sti,
                        "single_crossing": ex.check_single_crossing(fi, ALPHA, bi),
                        "beta_star_timeavg": ba, "status_timeavg": sta,
                        "interval_at_beta": {str(b): fi(b) for b in (0.25, 0.5, 1.0)},
                        "timeavg_at_beta": {str(b): fa(b) for b in (0.25, 0.5, 1.0)},
                        "realized_block_rate_at_beta_0.5": ch.flux(
                            "disc", blocked, intro=1.0, disc=0.5)}
        out["policies"][str(k)] = res
        resv = {}
        for pol, j in (("strike_all", None), ("batch_or_all", 4), ("poisson", None)):
            key = pol if j is None else f"{pol}_j{j}"
            resv[key] = {}
            for r in (0, 1, 2, 4):
                ch = ex.strategic_chain(k, pol, j=j, r=r)
                fi = lambda b, ch=ch: ch.window(T5, intro=1.0, disc=b) * a5
                fa = lambda b, ch=ch: ch.timeavg(intro=1.0, disc=b) * ca
                bi, sti = _bstar(fi)
                ba, sta = _bstar(fa)
                resv[key][str(r)] = {"states": ch.N, "beta_star_interval": bi,
                                     "status": sti, "beta_star_timeavg": ba,
                                     "status_timeavg": sta,
                                     "interval_at_beta_0.5": fi(0.5)}
        out["reserve"][str(k)] = resv
    # best timing policy for the time-average metric (average-reward MDP):
    # is it the strike-all policy?
    mdp = []
    for k, betas in ((8, [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]),
                     (32, [0.1, 0.25, 0.5, 0.75, 1.0, 1.5])):
        sa_root = out["policies"][str(k)]["strike_all"]["beta_star_timeavg"]
        sa_pol = np.zeros((k + 1, k + 1), dtype=int)
        for A in range(1, k + 1):
            sa_pol[A, A] = A
        sa = ex.strategic_chain(k, "strike_all")
        for beta in betas + [sa_root]:
            br = ex.censor_best_response_timeavg(k, 1.0, beta)
            valid = np.tril(np.ones((k + 1, k + 1), dtype=bool))
            same = bool(np.array_equal(br["policy"][valid], sa_pol[valid]))
            mdp.append({"kmax": k, "beta": beta,
                        "is_strike_all_root": beta == sa_root,
                        "optimal_down_fraction": br["g"],
                        "strike_all_down_fraction": 1.0 - sa.timeavg(intro=1.0, disc=beta),
                        "poisson_down_fraction": ex.pi0_geometric(beta, k),
                        "optimal_policy_equals_strike_all": same,
                        "rvi_iterations": br["iterations"], "rvi_span": br["span"]})
    out["best_response_timeavg_mdp"] = {
        "model": ("censor observes (A,D) and may block any b <= D discovered "
                  "units after any event; maximizes long-run P[A = 0]; "
                  "relative value iteration (exact.censor_best_response_timeavg)"),
        "rows": mdp,
        "all_optimal_equal_strike_all": all(m["optimal_policy_equals_strike_all"]
                                            for m in mdp),
        "max_abs_gap_down_fraction": max(abs(m["optimal_down_fraction"]
                                             - m["strike_all_down_fraction"])
                                         for m in mdp)}
    # Monte Carlo cross-check of the name-layer chain (no address layer)
    cases = (("strike_all", None, 0, 0.3), ("strike_all", None, 2, 0.6),
             ("batch", 4, 0, 0.6), ("batch_or_all", 4, 0, 0.6),
             ("poisson", None, 0, 0.8))
    args = [(8, beta, pol, j, r, MC_HORIZON, 1000 + 100 * ci + s)
            for ci, (pol, j, r, beta) in enumerate(cases) for s in range(MC_SEEDS)]
    allsims = _par_starmap(_mc_strategic, args)
    for ci, (pol, j, r, beta) in enumerate(cases):
        ch = ex.strategic_chain(8, pol, j=j, r=r)
        rec = {"policy": pol, "j": j, "r": r, "kmax": 8, "beta": beta}
        rec.update(_mc_summary(allsims[ci * MC_SEEDS:(ci + 1) * MC_SEEDS],
                               ch.window(T5, intro=1.0, disc=beta),
                               ch.timeavg(intro=1.0, disc=beta)))
        out["mc_check"].append(rec)
    out["state_space"] = ("(A,R,D): A active (served, discoverable) live units, "
                          "R reserve units (undiscoverable), D discovered-but-"
                          "unblocked active units; see exact.strategic_chain")
    return out


# =========================================================================== #
#  R5  diversification across providers
# =========================================================================== #
def _mc_providers(P, kp, beta, mode, horizon, seed, T=T5):
    rng = np.random.default_rng(seed)
    occ = np.zeros(P, dtype=int)
    t, warm = 0.0, 0.1 * horizon
    downs, dstart, up_time = [], 0.0, 0.0
    while t < horizon:
        nonfull = np.flatnonzero(occ < kp)
        nonempty = np.flatnonzero(occ > 0)
        if mode == "pooled":
            r_m = LAM_INTRO if nonfull.size else 0.0
            r_d = beta * LAM_INTRO if nonempty.size else 0.0
        else:
            r_m = LAM_INTRO / P * nonfull.size
            r_d = beta * LAM_INTRO / P * nonempty.size
        R = r_m + r_d
        dt = rng.exponential(1.0 / R)
        t_next = min(t + dt, horizon)
        was_up = bool(nonempty.size)
        if was_up and t_next > warm:
            up_time += t_next - max(t, warm)
        t += dt
        if t >= horizon:
            break
        if rng.random() * R < r_m:
            occ[nonfull[rng.integers(nonfull.size)]] += 1
        else:
            occ[nonempty[rng.integers(nonempty.size)]] = 0
        is_up = bool((occ > 0).any())
        if was_up and not is_up:
            dstart = t
        elif (not was_up) and is_up:
            downs.append((dstart, t))
    if not (occ > 0).any():
        downs.append((dstart, horizon))
    downs = [(s, e) for s, e in downs if e > warm]
    return interval_up_probability(downs, warm, horizon, T), up_time / (horizon - warm)


def r5_diversification():
    a5 = _addr(T5)
    ca = ex.addr_timeavg(N, LAM_A, MU)
    out = {"by_kmax": {}, "mc_check": []}
    betas_chk = np.round(np.linspace(0.05, 3.0, 60), 4)
    for K in (8, 16):
        fs_i = lambda b, K=K: ex.name_window_constant(b, K, T5) * a5
        fs_a = lambda b, K=K: (1.0 - ex.pi0_geometric(b, K)) * ca
        single = {"beta_star_interval": _bstar(fs_i)[0],
                  "beta_star_timeavg": _bstar(fs_a)[0],
                  "interval_at_beta_1": fs_i(1.0), "timeavg_at_beta_1": fs_a(1.0),
                  "realized_unit_burn_at_beta_1": 1.0 * (1.0 - ex.pi0_geometric(1.0, K))}
        rows = {}
        Ps = [1, 2, 4, 8] + ([16] if K == 16 else [])
        for P in Ps:
            kp = K // P
            rows[str(P)] = {"kp": kp}
            for mode in ("pooled", "idle"):
                ch = ex.providers_chain(P, kp, mode)
                fi = lambda b, ch=ch: ch.window(T5, intro=1.0, disc=b) * a5
                fa = lambda b, ch=ch: ch.timeavg(intro=1.0, disc=b) * ca
                units = lambda s, t: sum(l * c for l, c in enumerate(s)) - \
                    sum(l * c for l, c in enumerate(t))
                one = lambda s, t: 1.0
                bi, sti = _bstar(fi)
                rec = {"states": ch.N, "beta_star_interval": bi, "status": sti,
                       "single_crossing": ex.check_single_crossing(fi, ALPHA, bi),
                       "beta_star_timeavg": _bstar(fa)[0],
                       "interval_at_beta_1": fi(1.0), "timeavg_at_beta_1": fa(1.0),
                       "realized_unit_burn_at_beta_1": ch.flux("disc", units, intro=1.0, disc=1.0),
                       "takedown_events_at_beta_1": ch.flux("disc", one, intro=1.0, disc=1.0)}
                if mode == "pooled":
                    di = [fi(b) - fs_i(b) for b in betas_chk]
                    da = [fa(b) - fs_a(b) for b in betas_chk]
                    rec["max_excess_over_single_interval"] = float(np.max(di))
                    rec["max_excess_over_single_timeavg"] = float(np.max(da))
                rows[str(P)][mode] = rec
        out["by_kmax"][str(K)] = {"single_pool_unit_burns": single, "P": rows}
    # monotone recovery in P (pooled) at each kmax
    for K, blob in out["by_kmax"].items():
        seq = [blob["P"][str(P)]["pooled"]["beta_star_interval"] or 0.0
               for P in (1, 2, 4, 8)]
        blob["pooled_beta_star_nondecreasing_in_P"] = bool(
            all(b >= a for a, b in zip(seq, seq[1:])))
    cases = ((4, 2, 0.3, "pooled"), (2, 4, 0.1, "pooled"), (8, 2, 0.5, "pooled"),
             (8, 1, 1.0, "idle"))
    args = [(P, kp, beta, mode, MC_HORIZON, 2000 + 100 * ci + s)
            for ci, (P, kp, beta, mode) in enumerate(cases) for s in range(MC_SEEDS)]
    allsims = _par_starmap(_mc_providers, args)
    for ci, (P, kp, beta, mode) in enumerate(cases):
        ch = ex.providers_chain(P, kp, mode)
        rec = {"P": P, "kp": kp, "beta": beta, "mode": mode}
        rec.update(_mc_summary(allsims[ci * MC_SEEDS:(ci + 1) * MC_SEEDS],
                               ch.window(T5, intro=1.0, disc=beta),
                               ch.timeavg(intro=1.0, disc=beta)))
        out["mc_check"].append(rec)
    out["state_space"] = ("occupancy multiset (n_0..n_kp), n_l = #providers "
                          "holding l live units; see exact.providers_chain")
    out["coupling_argument"] = (
        "Couple the P-provider pooled model with the single pool of the same "
        "total buffer on the same Poisson clocks: a mint adds one unit to both "
        "whenever the total is below kmax, a takedown removes >=1 unit in the "
        "P-provider model and exactly 1 in the single pool. Hence K_P(t) <= "
        "K_1(t) pathwise, and every availability metric of the P-provider "
        "model is <= that of the unit-burn single pool, with equality at "
        "kp = 1 (P = kmax).")
    return out


# =========================================================================== #
#  R6  heavy-tailed discovery
# =========================================================================== #
def _discovery_laws():
    """Mean-1 discovery-delay laws: name -> (cdf, sampler, closed form or None,
    breakpoints for quadrature)."""
    laws = {}
    laws["deterministic"] = (lambda x: 1.0 * (x >= 1.0),
                             lambda rng, m: np.ones(m), np.exp(-MU), (1.0,))
    laws["exponential"] = (stats.expon(scale=1.0).cdf,
                           lambda rng, m: rng.exponential(1.0, m), 1 / (1 + MU), ())
    for kk in (2, 4):
        dist = stats.gamma(a=kk, scale=1.0 / kk)
        laws[f"erlang{kk}"] = (dist.cdf, lambda rng, m, d=dist: d.rvs(m, random_state=rng),
                               (kk / (kk + MU)) ** kk, ())
    for s in (0.5, 1.0, 1.5, 2.0):
        dist = stats.lognorm(s=s, scale=np.exp(-s * s / 2))
        laws[f"lognormal_s{s}"] = (dist.cdf, lambda rng, m, d=dist: d.rvs(m, random_state=rng),
                                   None, (0.01, 0.1, 1.0))
    for kk in (0.5, 2.0):
        dist = stats.weibull_min(c=kk, scale=1.0 / gamma_fn(1 + 1 / kk))
        laws[f"weibull_k{kk}"] = (dist.cdf, lambda rng, m, d=dist: d.rvs(m, random_state=rng),
                                  None, (0.01, 0.1, 1.0))
    for a in (1.5, 3.0):
        dist = stats.lomax(c=a, scale=a - 1.0)
        laws[f"lomax_a{a}"] = (dist.cdf, lambda rng, m, d=dist: d.rvs(m, random_state=rng),
                               None, (0.01, 0.1, 1.0))
    dist = stats.pareto(b=1.5, scale=1.0 / 3.0)
    laws["paretoI_a1.5"] = (dist.cdf, lambda rng, m, d=dist: d.rvs(m, random_state=rng),
                            None, (1.0 / 3.0, 1.0))
    w, m1, m2 = 0.9, 0.1, 9.1
    laws["hyperexp_0.9@0.1_0.1@9.1"] = (
        lambda x: w * (1 - np.exp(-x / m1)) + (1 - w) * (1 - np.exp(-x / m2)),
        lambda rng, m: np.where(rng.random(m) < w, rng.exponential(m1, m),
                                rng.exponential(m2, m)),
        w / (1 + MU * m1) + (1 - w) / (1 + MU * m2), (0.1, 1.0))
    return laws


def _nmin(p, alpha):
    if p <= 0:
        return 1
    n = 1
    while 1.0 - p ** n < alpha:
        n += 1
        if n > 10000:
            return None
    return n


def r6_heavy_tail():
    rng = np.random.default_rng(20261003)
    M = 4_000_000
    rows = []
    for name, (cdf, sampler, closed, bps) in _discovery_laws().items():
        p_q, err = ex.laplace_from_cdf(cdf, MU, bps)
        D = sampler(rng, M)
        eD = np.exp(-MU * D)
        I = rng.exponential(1.0 / MU, M)
        ov = MU * np.maximum(I - D, 0.0)
        rows.append({
            "law": name, "mean_D_mc": float(D.mean()),
            "p_quadrature": p_q, "quad_abs_err": err, "p_closed_form": closed,
            "p_mc": float(eD.mean()), "p_mc_se": float(eD.std() / np.sqrt(M)),
            "identity_mu_E_overlap_mc": float(ov.mean()),
            "identity_mc_se": float(ov.std() / np.sqrt(M)),
            "identity_minus_p_quadrature": float(ov.mean() - p_q),
            "p_pow_8": p_q ** 8, "c_a_n8": 1 - p_q ** 8,
            "n_min_ca_0.95": _nmin(p_q, 0.95), "n_min_ca_0.99": _nmin(p_q, 0.99)})
    exp_p = 1 / (1 + MU)
    return {"mu": MU, "mean_D": 1.0, "mc_samples": M, "rows": rows,
            "identity": "mu E[(I-D)^+] = E[exp(-mu D)] = P(D < I), I ~ Exp(mu)",
            "exponential_p": exp_p,
            "laws_with_p_above_exponential": [r["law"] for r in rows
                                              if r["p_quadrature"] > exp_p + 1e-9],
            "laws_with_p_below_exponential": [r["law"] for r in rows
                                              if r["p_quadrature"] < exp_p - 1e-9],
            "notes": ("Jensen: deterministic D minimizes p at fixed mean; "
                      "completely monotone D (exponential mixtures) have "
                      "p >= 1/(1+mu E[D]); sup p = 1 over mean-1 laws.")}


# =========================================================================== #
#  R7  synchronized discovery
# =========================================================================== #
def _mc_sweep(n, s, horizon, seed):
    rng = np.random.default_rng(seed)
    clear = np.ones(n, dtype=bool)
    t, warm, zero_t = 0.0, 0.1 * horizon, 0.0
    while t < horizon:
        c = int(clear.sum())
        r_ind = (1 - s) * LAM_A * c
        r_sw = s * LAM_A if c >= 1 else 0.0
        r_rot = MU * (n - c)
        R = r_ind + r_sw + r_rot
        dt = rng.exponential(1.0 / R)
        t_next = min(t + dt, horizon)
        if c == 0 and t_next > warm:
            zero_t += t_next - max(t, warm)
        t += dt
        if t >= horizon:
            break
        u = rng.random() * R
        if u < r_ind:
            idx = np.flatnonzero(clear)
            clear[idx[rng.integers(idx.size)]] = False
        elif u < r_ind + r_sw:
            clear[:] = False
        else:
            idx = np.flatnonzero(~clear)
            clear[idx[rng.integers(idx.size)]] = True
    return zero_t / (horizon - warm)


def r7_sync():
    ns = [2, 4, 8, 16]
    ss = [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0]
    p = LAM_A / (LAM_A + MU)
    rows = []
    for n in ns:
        for s in ss:
            Q = ex.addr_sweep_generator(n, LAM_A, MU, s)
            pi = ex.ctmc_stationary(Q)
            up = np.arange(n + 1) >= 1
            w5 = ex.ctmc_window(Q, up, T5, pi=pi)
            marg = float(pi @ (n - np.arange(n + 1))) / n
            rows.append({"n": n, "s": s, "P_c0": float(pi[0]), "p_pow_n": p ** n,
                         "sweep_closed_form": LAM_A / (LAM_A + n * MU) if s == 1.0 else None,
                         "per_endpoint_blocked_marginal": marg,
                         "c_a": 1 - float(pi[0]), "addr_window_T5": w5})
    # consequences at the canonical n=8, kmax=8
    cons = []
    for s in ss:
        Q = ex.addr_sweep_generator(N, LAM_A, MU, s)
        pi = ex.ctmc_stationary(Q)
        ca = 1 - float(pi[0])
        w5 = ex.ctmc_window(Q, np.arange(N + 1) >= 1, T5, pi=pi)
        bavg = ex.beta_star(lambda b: (1 - ex.pi0_geometric(b, KMAX)) * ca, ALPHA)[0] \
            if ca > ALPHA else None
        bint = ex.beta_star(lambda b: ex.name_window_constant(b, KMAX, T5) * w5, ALPHA)[0]
        cons.append({"s": s, "c_a": ca, "addr_window_T5": w5,
                     "beta_star_avg_kmax8": bavg, "beta_star_interval_kmax8": bint})
    mc = []
    cases = ((4, 1.0), (4, 0.1), (2, 0.5), (8, 1.0))
    args = [(n, s, 4.0e4, 3000 + 100 * ci + k)
            for ci, (n, s) in enumerate(cases) for k in range(MC_SEEDS)]
    allsims = _par_starmap(_mc_sweep, args)
    for ci, (n, s) in enumerate(cases):
        sims = np.array(allsims[ci * MC_SEEDS:(ci + 1) * MC_SEEDS])
        Q = ex.addr_sweep_generator(n, LAM_A, MU, s)
        exact_p0 = float(ex.ctmc_stationary(Q)[0])
        se = float(sims.std(ddof=1) / np.sqrt(len(sims)))
        mc.append({"n": n, "s": s, "exact_P_c0": exact_p0,
                   "mc_P_c0": float(sims.mean()), "mc_se": se,
                   "z": float((sims.mean() - exact_p0) / se), "mc_seeds": len(sims),
                   "mc_horizon": 4.0e4})
    return {"model": "c->c+1 at mu(n-c); c->c-1 at (1-s) lam_a c; c->0 at s lam_a",
            "rows": rows, "canonical_consequences": cons, "mc_check": mc}


# =========================================================================== #
#  R8  mint-time exposure
# =========================================================================== #
def _mc_exposure(kmax, beta, rho, theta, horizon, seed, T=T5):
    rng = np.random.default_rng(seed)
    E = U = 0
    t, warm = 0.0, 0.1 * horizon
    downs, dstart, up_time = [], 0.0, 0.0
    while t < horizon:
        L = E + U
        r_m = LAM_INTRO if L < kmax else 0.0
        r_p = theta * E
        r_u = beta if L >= 1 else 0.0
        R = r_m + r_p + r_u
        dt = rng.exponential(1.0 / R)
        t_next = min(t + dt, horizon)
        was_up = L >= 1
        if was_up and t_next > warm:
            up_time += t_next - max(t, warm)
        t += dt
        if t >= horizon:
            break
        u = rng.random() * R
        if u < r_m:
            if rng.random() < rho:
                E += 1
            else:
                U += 1
        elif u < r_m + r_p:
            E -= 1
        else:
            if rng.random() * L < E:
                E -= 1
            else:
                U -= 1
        is_up = E + U >= 1
        if was_up and not is_up:
            dstart = t
        elif (not was_up) and is_up:
            downs.append((dstart, t))
    if E + U == 0:
        downs.append((dstart, horizon))
    downs = [(s, e) for s, e in downs if e > warm]
    return interval_up_probability(downs, warm, horizon, T), up_time / (horizon - warm)


def _exposure_window_fn(kmax, rho, theta, a5):
    if theta == np.inf:
        if rho >= 1.0:
            return lambda b: 0.0
        li = (1.0 - rho) * LAM_INTRO
        return lambda b: ex.bd_window(*ex.name_rates_constant(kmax, li, b), T5) * a5
    ch = ex.exposure_chain(kmax, rho)
    return lambda b: ch.window(T5, intro=1.0, disc=b, theta=theta) * a5


def r8_exposure():
    a5 = _addr(T5)
    rhos = [0.0, 0.25, 0.5, 0.75, 0.9, 1.0]
    thetas = [np.inf, 10.0, 1.0, 0.1]
    table = {}
    for k in (8, 32):
        table[str(k)] = {}
        for th in thetas:
            key = "inf" if th == np.inf else str(th)
            table[str(k)][key] = {}
            for rho in rhos:
                f = _exposure_window_fn(k, rho, th, a5)
                b, st = _bstar(f)
                table[str(k)][key][str(rho)] = {"beta_star_interval": b, "status": st}
    # theta = infinity == single pool with intro (1-rho) lam_intro
    lim = []
    for rho in (0.25, 0.5, 0.9):
        for th in (1e3, 1e4):
            ch = ex.exposure_chain(8, rho)
            d = []
            for beta in (0.1, 0.3, 0.6):
                w_ch = ch.window(T5, intro=1.0, disc=beta, theta=th)
                w_sp = ex.bd_window(*ex.name_rates_constant(8, 1 - rho, beta), T5)
                d.append(abs(w_ch - w_sp))
            lim.append({"rho": rho, "theta": th, "max_abs_diff_window": float(max(d))})
    # the 'beta_eff' view of theta=inf: beta*(rho) vs (1-rho) beta*(0)
    mc = []
    cases = ((0.5, 1.0, 0.3), (0.9, 10.0, 0.05), (1.0, 0.1, 0.5), (0.75, 1.0, 0.2))
    args = [(8, beta, rho, th, MC_HORIZON, 4000 + 100 * ci + s)
            for ci, (rho, th, beta) in enumerate(cases) for s in range(MC_SEEDS)]
    allsims = _par_starmap(_mc_exposure, args)
    for ci, (rho, th, beta) in enumerate(cases):
        ch = ex.exposure_chain(8, rho)
        rec = {"rho": rho, "theta": th, "beta": beta, "kmax": 8}
        rec.update(_mc_summary(allsims[ci * MC_SEEDS:(ci + 1) * MC_SEEDS],
                               ch.window(T5, intro=1.0, disc=beta, theta=th),
                               ch.timeavg(intro=1.0, disc=beta, theta=th)))
        mc.append(rec)
    return {"rhos": rhos, "thetas": ["inf", 10.0, 1.0, 0.1], "table": table,
            "theta_inf_limit_check": lim, "mc_check": mc,
            "units": "theta in units of lam_intro; beta = lam_disc/lam_intro "
                     "with lam_intro counting every mint (exposed or not)",
            "state_space": "(E,U) with E+U <= kmax; see exact.exposure_chain"}


# =========================================================================== #
#  R9  range blocking (crisis regime)
# =========================================================================== #
def _mc_range(n_tot, g, horizon, seed, space_bits=40):
    """Literal simulation: rotations draw uniform addresses from a space of
    2^space_bits addresses whose lowest fraction g is range-blocked; individual
    discoveries add the endpoint's address to a persistent blocklist."""
    rng = np.random.default_rng(seed)
    Nsp = 1 << space_bits
    cut = int(g * Nsp)
    blocklist = set()
    addr = rng.integers(cut, Nsp, n_tot) if g < 1 else rng.integers(0, Nsp, n_tot)
    blocked = np.array([(a < cut) or (int(a) in blocklist) for a in addr])
    rate = n_tot * (MU + LAM_A)
    nev = rng.poisson(rate * horizon)
    times = np.sort(rng.uniform(0.0, horizon, nev))
    who = rng.integers(0, n_tot, nev)
    rot = rng.random(nev) < MU / (MU + LAM_A)
    newaddr = rng.integers(0, Nsp, nev)
    warm = 0.1 * horizon
    subsets = [2, 4, 8, 16]
    all_t = {m: 0.0 for m in subsets}
    blk_t = np.zeros(n_tot)
    last = 0.0
    for t, i, isrot, a in zip(times, who, rot, newaddr):
        if t > warm:
            seg = t - max(last, warm)
            blk_t += blocked * seg
            for m in subsets:
                if m <= n_tot and blocked[:m].all():
                    all_t[m] += seg
        last = t
        if isrot:                       # fresh uniform address
            addr[i] = a
            blocked[i] = (a < cut) or (int(a) in blocklist)
        elif not blocked[i]:            # discovery blocks the current address
            blocklist.add(int(addr[i]))
            blocked[i] = True
    seg = horizon - max(last, warm)
    blk_t += blocked * seg
    for m in subsets:
        if m <= n_tot and blocked[:m].all():
            all_t[m] += seg
    meas = horizon - warm
    return blk_t.mean() / meas, {m: all_t[m] / meas for m in subsets}, len(blocklist) / Nsp


def r9_range():
    gs = [0.0, 0.1, 0.42, 0.83, 0.95, 1.0]
    ns = [2, 4, 8, 16]
    Ps = [1, 2, 4]
    table = []
    for g in gs:
        for n in ns:
            for P in Ps:
                if n % P:
                    table.append({"g": g, "n": n, "P": P, "applicable": False})
                    continue
                k = n // P
                all_hit = ex.address_factor_providers([g] * P, [k] * P, LAM_A, MU)
                one_hit = ex.address_factor_providers([g] + [0.0] * (P - 1),
                                                      [k] * P, LAM_A, MU)
                w_all = ex.addr_window_providers([g] * P, [k] * P, LAM_A, MU, T5)
                w_one = ex.addr_window_providers([g] + [0.0] * (P - 1), [k] * P,
                                                 LAM_A, MU, T5)
                table.append({"g": g, "n": n, "P": P, "applicable": True,
                              "p_g": ex.p_range(g, LAM_A, MU),
                              "factor_all_providers_hit": all_hit,
                              "factor_one_provider_hit": one_hit,
                              "window_T5_all_providers_hit": w_all,
                              "window_T5_one_provider_hit": w_one})
    # simulation check of p(g) and p(g)^n
    sim = []
    args = [(16, g, 4000.0, 5000 + 100 * gi + s)
            for gi, g in enumerate(gs) for s in range(MC_SEEDS)]
    allreps = _par_starmap(_mc_range, args)
    for gi, g in enumerate(gs):
        reps = allreps[gi * MC_SEEDS:(gi + 1) * MC_SEEDS]
        sq = np.sqrt(len(reps))
        pbl = np.array([r[0] for r in reps])
        rec = {"g": g, "p_formula": ex.p_range(g, LAM_A, MU),
               "p_sim": float(pbl.mean()), "p_sim_se": float(pbl.std(ddof=1) / sq),
               "blocklist_fraction_of_space": float(np.mean([r[2] for r in reps])),
               "mc_seeds": len(reps), "mc_horizon": 4000.0, "endpoints": 16}
        for m in ns:
            v = np.array([r[1][m] for r in reps])
            rec[f"all{m}_formula"] = ex.p_range(g, LAM_A, MU) ** m
            rec[f"all{m}_sim"] = float(v.mean())
            rec[f"all{m}_sim_se"] = float(v.std(ddof=1) / sq)
        sim.append(rec)
    # regime average
    reg = []
    for gc in (0.42, 0.83, 0.95, 1.0):
        for pc in (0.0, 0.01, 0.05, 0.1, 0.25):
            for P in Ps:
                for mode in ("common", "independent"):
                    reg.append({"g_crisis": gc, "pi_c": pc, "n": 8, "P": P, "mode": mode,
                                "address_factor": ex.address_factor_regime(
                                    gc, pc, 8, P, LAM_A, MU, mode=mode)})
    # consequences for the frontier at n=8
    cons = []
    for g in gs:
        for P, scen in ((1, "all"), (2, "one")):
            gg = [g] if P == 1 else [g, 0.0]
            kk = [8] if P == 1 else [4, 4]
            ca = ex.address_factor_providers(gg, kk, LAM_A, MU)
            w5 = ex.addr_window_providers(gg, kk, LAM_A, MU, T5)
            rec = {"g": g, "P": P, "scenario": scen, "c_a": ca, "addr_window_T5": w5}
            for k in (8, 32):
                rec[f"beta_star_avg_kmax{k}"] = ex.beta_star(
                    lambda b, k=k: (1 - ex.pi0_geometric(b, k)) * ca, ALPHA)[0] \
                    if ca > ALPHA else None
                rec[f"beta_star_interval_kmax{k}"] = ex.beta_star(
                    lambda b, k=k: ex.name_window_constant(b, k, T5) * w5, ALPHA)[0]
            cons.append(rec)
    return {"model": "p(g) = g + (1-g) lam_a/(lam_a+mu); factor 1 - prod p(g_i)^n_i",
            "derivation": ("An endpoint leaves 'clear' at rate lam_a + mu g "
                           "(discovery, or a rotation landing in the blocked "
                           "range) and leaves 'blocked' at rate mu (1-g) (a "
                           "rotation landing in clear space); the stationary "
                           "blocked probability of this two-state chain is "
                           "(lam_a + mu g)/(lam_a + mu) = g + (1-g) lam_a/(lam_a+mu)."),
            "table": table, "sim_check": sim, "regime_average": reg,
            "frontier_consequences_n8": cons,
            "api": ("exact.p_range, exact.address_factor_providers, "
                    "exact.address_factor_regime, exact.addr_window_range, "
                    "exact.addr_window_providers")}


# =========================================================================== #
#  R10 per-unit discovery normalizations
# =========================================================================== #
def r10_perunit():
    a5 = _addr(T5)
    out = {}
    norms = {
        "constant_rate": None,
        "delta=lam_disc/kmax": lambda b, k: b / k,
        "delta=lam_disc/E_const[K]": lambda b, k: b / ex.meanK_geometric(b, k),
        "delta=lam_disc": lambda b, k: b,
    }
    for k in (8,):
        out[str(k)] = {}
        for name, dfun in norms.items():
            if dfun is None:
                f = lambda b, k=k: ex.name_window_constant(b, k, T5) * a5
                bs, st = _bstar(f)
                pi0 = ex.pi0_geometric(bs, k)
                rec = {"beta_star_interval": bs, "pi0_at_beta_star": pi0,
                       "mean_K_at_beta_star": ex.meanK_geometric(bs, k),
                       "realized_burn_at_beta_star": bs * (1 - pi0)}
            else:
                f = lambda b, k=k, dfun=dfun: ex.name_window_perunit(dfun(b, k), k, T5) * a5
                bs, st = _bstar(f)
                delta = dfun(bs, k)
                bb, dd = ex.name_rates_perunit(k, LAM_INTRO, delta)
                pi = ex.bd_stationary(bb, dd)
                EK = float(pi @ np.arange(k + 1))
                rec = {"beta_star_interval": bs, "delta_at_beta_star": delta,
                       "pi0_at_beta_star": float(pi[0]), "mean_K_at_beta_star": EK,
                       "realized_burn_at_beta_star": delta * EK}
            rec["status"] = st
            rec["single_crossing"] = ex.check_single_crossing(f, ALPHA, bs)
            # pi0 at reference betas (0.8 and 1.6: the paper's worked example)
            refs = {}
            for b in (0.8, 1.0, 1.6):
                if dfun is None:
                    refs[str(b)] = ex.pi0_geometric(b, k)
                else:
                    bb, dd = ex.name_rates_perunit(k, LAM_INTRO, dfun(b, k))
                    refs[str(b)] = float(ex.bd_stationary(bb, dd)[0])
            rec["pi0_at_beta"] = refs
            out[str(k)][name] = rec
    return {"kmax": 8, "T": T5, "alpha": ALPHA, "results": out,
            "note": "realized burn = delta E[K] (units/time, lam_intro = 1)"}


# =========================================================================== #
#  R11 illustrative adversary profiles (censor_models.py)
# =========================================================================== #
def r11_profiles():
    profiles = {"GFW-like": 1.5, "TSPU-like": 0.8, "Iran-like": 1.0}
    ns = [2, 4, 6, 8, 12]
    ks = [4, 8, 16, 32]
    out = {}
    for name, la in profiles.items():
        out[name] = {"lam_a": la, "mu_over_lam_a": MU / la, "by_n": {}}
        for n in ns:
            w5 = ex.addr_window(n, la, MU, T5)
            ca = ex.addr_timeavg(n, la, MU)
            rec = {"addr_window_T5": w5, "c_a": ca, "beta_star_interval": {},
                   "beta_star_avg": {}}
            for k in ks:
                rec["beta_star_interval"][str(k)] = _bstar(
                    lambda b, k=k: ex.name_window_constant(b, k, T5) * w5)[0]
                rec["beta_star_avg"][str(k)] = ex.beta_star_avg(ALPHA, k, n, la, MU)[0]
            out[name]["by_n"][str(n)] = rec
    return {"profiles": out, "T": T5, "alpha": ALPHA, "mu": MU,
            "note": "gamma and lam_disc_scale of censor_models.py are not used "
                    "(no address cap is modeled, i.e. gamma = 1)"}


# =========================================================================== #
#  R13 rotation speed under both metrics (supports the claim that faster
#  rotation stops moving the frontier once mu/lam_a is moderate)
# =========================================================================== #
def r13_rotation():
    ratios = np.geomspace(0.5, 128.0, 49)
    tols = (0.01, 0.001)
    rows = []
    for n in (4, 8, 16):
        for k in (8, 32):
            bi_inf = ex.beta_star(lambda b, k=k: ex.name_window_constant(b, k, T5), ALPHA)[0]
            ba_inf = ex.beta_star(lambda b, k=k: 1.0 - ex.pi0_geometric(b, k), ALPHA)[0]
            for la in (1.0, 10.0, 60.0):
                bi, ba, aw, ca = [], [], [], []
                for r in ratios:
                    mu = r * la
                    bi.append(ex.frontier_interval(ALPHA, T5, n, la, mu, k)[0])
                    ba.append(ex.frontier_timeavg(ALPHA, n, la, mu, k)[0])
                    aw.append(ex.addr_window(n, la, mu, T5))
                    ca.append(ex.addr_timeavg(n, la, mu))

                def sat(vals, lim, tol):
                    ok = [v is not None and v >= lim - tol for v in vals]
                    for i in range(len(ok)):
                        if all(ok[i:]):
                            return float(ratios[i])
                    return None
                rows.append({
                    "n": n, "kmax": k, "lam_a_over_lam_intro": la,
                    "lam_a_T": la * T5,
                    "beta_star_interval_limit_mu_inf": bi_inf,
                    "beta_star_timeavg_limit_mu_inf": ba_inf,
                    "beta_star_interval": bi, "beta_star_timeavg": ba,
                    "addr_window_T5": aw, "c_a": ca,
                    "saturation_ratio_interval": {str(t): sat(bi, bi_inf, t) for t in tols},
                    "saturation_ratio_timeavg": {str(t): sat(ba, ba_inf, t) for t in tols},
                    "min_ratio_any_interval_frontier": next(
                        (float(r) for r, v in zip(ratios, bi) if v is not None), None),
                })
    # timescale caveat: canonical n = 8, mu/lam_a = 3, but lam_a/lam_intro varies
    from scipy.optimize import brentq
    las = [1.0, 3.0, 10.0, 20.0, 30.0, 40.0, 60.0, 100.0]
    win = [ex.addr_window(N, la, 3.0 * la, T5) for la in las]
    la_cross = brentq(lambda la: ex.addr_window(N, la, 3.0 * la, T5) - ALPHA, 1.0, 100.0,
                      xtol=1e-8)
    timescale = {"n": N, "mu_over_lam_a": 3.0, "T": T5,
                 "lam_a_over_lam_intro": las, "addr_window_T5": win,
                 "lam_a_over_lam_intro_where_window_equals_alpha": la_cross,
                 "note": ("above this ratio the address layer alone is below "
                          "alpha, so no beta meets (alpha, T)")}
    return {"ratios_mu_over_lam_a": ratios, "T": T5, "alpha": ALPHA,
            "definition": ("saturation ratio = smallest mu/lam_a on the grid from "
                           "which beta* stays within tol of its mu -> infinity "
                           "limit (address layer perfect)"),
            "rows": rows, "timescale_caveat_canonical": timescale}


# =========================================================================== #
#  Figures
# =========================================================================== #
def _fig_setup():
    from figstyle import use_style
    import matplotlib.pyplot as plt
    use_style()
    # final-size fonts (figures are drawn at the 3.33 in column width)
    plt.rcParams.update({"font.size": 7.5, "axes.labelsize": 8,
                         "xtick.labelsize": 7, "ytick.labelsize": 7,
                         "legend.fontsize": 7, "axes.titlesize": 7.5,
                         "lines.linewidth": 1.3, "lines.markersize": 3.2})
    return plt


# secondary encodings so identity never rests on colour alone
LS = ["-", (0, (5, 1.6)), (0, (3, 1.2, 1, 1.2)), (0, (1, 1.1)), (0, (7, 1.5, 1.5, 1.5))]
MK = ["o", "s", "^", "D", "v"]


def _hollow(c, ms=2.8):
    return dict(ms=ms, mfc="white", mec=c, mew=0.8, clip_on=False, zorder=4)


def figures():
    plt = _fig_setup()
    from matplotlib.lines import Line2D
    from figstyle import COL, tidy
    REF = dict(color="#3a3a3a", lw=0.8, alpha=0.75, ls=":")
    GRAY = "#6b6b6b"
    INK = "#444444"
    a5 = _addr(T5)
    written = []

    def save(fig, name):
        p = os.path.join(FIGDIR, name)
        fig.savefig(p)
        plt.close(fig)
        written.append(p)

    # ---- (a) interval availability vs beta: exact lines + simulated E2 points
    with open(os.path.join(RESULTS, "E2_phase_transition.json")) as f:
        e2 = json.load(f)
    fig, ax = plt.subplots(figsize=(3.33, 2.3))
    bg = np.linspace(0.2, 2.0, 361)
    ks = [4, 8, 16, 32, 64]
    styles = [LS[0], LS[1], LS[2], (0, (4, 1, 1, 1, 1, 1)), LS[4]]
    handles = []
    for i, k in enumerate(ks):
        y = np.array([ex.name_window_constant(b, k, T5) * a5 for b in bg])
        ax.plot(bg, y, ls=styles[i], color=COL[i], lw=1.4, zorder=3)
        has_sim = str(k) in e2["curves"]
        if has_sim:
            sb = np.array(e2["betas"])[::2]
            sv = np.array(e2["curves"][str(k)]["interval"])[::2]
            ax.plot(sb, sv, MK[i], ls="none", **_hollow(COL[i]))
        handles.append(Line2D([], [], color=COL[i], ls=styles[i], lw=1.4,
                              marker=MK[i] if has_sim else None, ms=2.8,
                              mfc="white", mec=COL[i], mew=0.8,
                              label=fr"$k_{{\max}}={k}$"))
    ax.axhline(ALPHA, **REF)
    ax.axvline(1.0, color=GRAY, lw=0.7, alpha=0.6)
    ax.text(1.985, ALPHA + 0.012, r"$\alpha=0.95$", fontsize=7, ha="right",
            va="bottom", color=INK)
    ax.text(1.02, 0.03, r"$\beta=1$", fontsize=7, color=INK, va="bottom")
    ax.text(0.23, 0.05, "lines: exact CTMC\nmarkers: simulation (E2)",
            fontsize=7, color=INK, va="bottom")
    ax.set_xlabel(r"burn ratio $\beta=\lambda_{\mathrm{disc}}/\lambda_{\mathrm{intro}}$")
    ax.set_ylabel(r"interval availability ($T=5$)")
    ax.set_xlim(0.2, 2.0)
    ax.set_ylim(0, 1.02)
    tidy(ax)
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 0.91),
              ncol=1, frameon=False, handlelength=2.4, handletextpad=0.4,
              labelspacing=0.25, borderaxespad=0.1)
    save(fig, "fig_phase_exact.pdf")

    # ---- (b) exact interval frontier beta*(alpha, T=5) vs kmax
    with open(os.path.join(RESULTS, "R2_frontiers.json")) as f:
        r2 = json.load(f)
    kd = np.array(r2["dense"]["kmax"])
    fig, ax = plt.subplots(figsize=(3.33, 2.3))
    ax.axhline(1.0, color=GRAY, lw=0.7, alpha=0.6)
    ax.axhline(r2["c_a"] / 0.95, color=GRAY, lw=0.8, ls=":")
    ax.text(2.15, 1.0 - 0.012, r"$\beta=1$", fontsize=7, color=INK, va="top")
    ax.text(2.15, r2["c_a"] / 0.95 + 0.008, r"$c_a/\alpha$ ($\alpha=0.95$)",
            fontsize=7, color=INK, va="bottom")
    ya = np.array([np.nan if v is None else v for v in r2["dense"]["avg"]["0.95"]])
    ax.plot(kd, ya, ls=(0, (6, 1.5, 1.5, 1.5)), color="#555555", lw=1.0,
            label=r"$\beta^\star_{\mathrm{avg}}$, $\alpha=0.95$ (time average)")
    for i, a in enumerate(R2_ALPHA):
        y = np.array([np.nan if v is None else v
                      for v in r2["dense"]["interval"][f"{a}|5.0"]])
        kc = r2["min_kmax_beta_star_above_1"][str(a)]["5.0"]["kmax"]
        ax.plot(kd, y, ls=LS[i], color=COL[i], lw=1.4,
                label=fr"$\beta^\star$, $\alpha={a}$ ($>1$ from $k_{{\max}}={kc}$)")
        if kc is not None and kc <= kd.max():
            ax.plot([kc], [1.0], MK[i], **_hollow(COL[i], ms=3.6))
    ax.set_xscale("log", base=2)
    ax.set_xlim(2, kd.max())
    ticks = [2, 8, 32, 128, 512, 2048]
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])
    ax.set_ylim(0, 1.12)
    ax.set_xlabel(r"buffer $k_{\max}$ (live units)")
    ax.set_ylabel(r"frontier $\beta^\star$ ($T=5$)")
    tidy(ax)
    ax.legend(loc="lower right", frameon=False, handlelength=2.4, borderaxespad=0.2,
              labelspacing=0.3)
    save(fig, "fig_frontier_kmax.pdf")

    # ---- (c) robustness panels (interval frontier, alpha = 0.95, T = 5)
    with open(os.path.join(RESULTS, "E7_bursty_burns.json")) as f:
        e7 = json.load(f)
    with open(os.path.join(RESULTS, "R4_strategic_censor.json")) as f:
        r4 = json.load(f)
    with open(os.path.join(RESULTS, "R5_diversification.json")) as f:
        r5 = json.load(f)
    with open(os.path.join(RESULTS, "R8_mint_exposure.json")) as f:
        r8 = json.load(f)
    bg = np.linspace(0.01, 1.6, 160)
    burst_curves = {}
    for bb in [1, 2, 4, 8]:
        ch = ex.batch_name_chain(KMAX, bb)
        burst_curves[bb] = [ch.window(T5, intro=1.0, disc=b) * a5 for b in bg]

    def draw_robustness(axs, ylabel_axes):
        # (a) bursty burns: availability vs beta at kmax = 8, exact + E7 markers
        ax = axs[0]
        for i, bb in enumerate([1, 2, 4, 8]):
            ax.plot(bg, burst_curves[bb], ls=LS[i], color=COL[i], label=fr"$b={bb}$")
            sb = np.array(e7["betas"])[::3]
            sv = np.array(e7["curves"][str(bb)]["interval"])[::3]
            ax.plot(sb, sv, MK[i], ls="none", **_hollow(COL[i], ms=2.4))
        ax.axhline(ALPHA, **REF)
        ax.axvline(1.0, color=GRAY, lw=0.6, alpha=0.6)
        ax.set_xlim(0, 1.6)
        ax.set_ylim(0, 1.03)
        ax.set_xlabel(r"burn ratio $\beta$")
        ax.set_title("(a) bursty burns", loc="left", pad=3)
        tidy(ax)
        hs = [Line2D([], [], color=COL[i], ls=LS[i], marker=MK[i], ms=2.4, mfc="white",
                     mec=COL[i], mew=0.8, label=fr"$b={bb}$")
              for i, bb in enumerate([1, 2, 4, 8])]
        ax.legend(handles=hs, loc="lower left", frameon=False, handlelength=2.0,
                  borderaxespad=0.1, labelspacing=0.2)
        # (b) strategic timing: beta* vs reserve r, strike-all vs Poisson
        ax = axs[1]
        rs = [0, 1, 2, 4]
        for i, k in enumerate(["8", "32"]):
            y = [r4["reserve"][k]["strike_all"][str(r)]["beta_star_interval"] for r in rs]
            ax.plot(rs, y, ls=LS[i], marker=MK[i], color=COL[i], label=fr"${k}$",
                    **{k2: v for k2, v in _hollow(COL[i], ms=3.0).items() if k2 != "zorder"})
            pz = r4["policies"][k]["poisson"]["beta_star_interval"]
            ax.axhline(pz, color=COL[i], lw=0.8, ls=":")
            ax.text(-0.1, pz + 0.012, fr"Poisson, $k_{{\max}}={k}$", fontsize=7,
                    color=INK, ha="left", va="bottom")
        ax.set_xlim(-0.15, 4.15)
        ax.set_xticks(rs)
        ax.set_ylim(0, 1.08)
        ax.set_xlabel(r"defender reserve $r$")
        ax.set_title("(b) strategic timing", loc="left", pad=3)
        tidy(ax)
        ax.legend(loc="lower right", frameon=False, handlelength=2.0, borderaxespad=0.1,
                  ncol=2, columnspacing=0.8, title=r"strike-all, $k_{\max}=$",
                  title_fontsize=7)
        # (c) diversification: beta* vs P (pooled minting, full-capacity censor)
        ax = axs[2]
        Ps = [1, 2, 4, 8]
        for i, K in enumerate(["8", "16"]):
            y = [r5["by_kmax"][K]["P"][str(P)]["pooled"]["beta_star_interval"] for P in Ps]
            ax.plot(Ps, y, ls=LS[i], marker=MK[i], color=COL[i],
                    label=fr"pooled, $k_{{\max}}={K}$",
                    **{k2: v for k2, v in _hollow(COL[i], ms=3.0).items() if k2 != "zorder"})
            sp_ = r5["by_kmax"][K]["single_pool_unit_burns"]["beta_star_interval"]
            ax.axhline(sp_, color=COL[i], lw=0.8, ls=":")
        yi = [r5["by_kmax"]["8"]["P"][str(P)]["idle"]["beta_star_interval"] for P in Ps]
        ax.plot(Ps, yi, ls=LS[4], marker=MK[2], color=GRAY, lw=1.0,
                label="idle-clock model (E9)",
                **{k2: v for k2, v in _hollow(GRAY, ms=3.0).items() if k2 != "zorder"})
        ax.set_xscale("log", base=2)
        ax.set_xticks(Ps)
        ax.set_xticklabels([str(P) for P in Ps])
        ax.plot([], [], ls=":", color=GRAY, lw=0.9, label="single pool")
        ax.set_xlim(0.88, 9.1)
        ax.set_ylim(0, 1.75)
        ax.set_xlabel(r"providers $P$")
        ax.set_title("(c) diversification", loc="left", pad=3)
        tidy(ax)
        ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0), frameon=False,
                  handlelength=2.0, borderaxespad=0.1, labelspacing=0.2)
        # (d) mint-time exposure: beta* vs rho at kmax = 8
        ax = axs[3]
        rhos = r8["rhos"]
        labs = {"inf": r"$\theta=\infty$", "10.0": r"$\theta=10$", "1.0": r"$\theta=1$",
                "0.1": r"$\theta=0.1$"}
        for i, key in enumerate(["inf", "10.0", "1.0", "0.1"]):
            y = [r8["table"]["8"][key][str(r)]["beta_star_interval"] for r in rhos]
            y = [0.0 if v is None else v for v in y]
            ax.plot(rhos, y, ls=LS[i], marker=MK[i], color=COL[i], label=labs[key],
                    **{k2: v for k2, v in _hollow(COL[i], ms=2.8).items() if k2 != "zorder"})
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 0.72)
        ax.set_xlabel(r"exposed share of mints $\rho$")
        ax.set_title("(d) mint-time exposure", loc="left", pad=3)
        tidy(ax)
        ax.legend(loc="lower left", frameon=False, handlelength=2.0, borderaxespad=0.1,
                  labelspacing=0.2)
        ylab = ["interval availability", r"frontier $\beta^\star$",
                r"frontier $\beta^\star$", r"frontier $\beta^\star$"]
        for i in ylabel_axes:
            axs[i].set_ylabel(ylab[i])

    # single-column 2 x 2 version
    fig, axs = plt.subplots(2, 2, figsize=(3.33, 3.3))
    draw_robustness([axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1]], [0, 1, 2, 3])
    fig.tight_layout(pad=0.2, h_pad=0.6, w_pad=0.6)
    save(fig, "fig_robustness.pdf")
    # full-width 1 x 4 version (figure*, textwidth about 7.0 in)
    fig, axs = plt.subplots(1, 4, figsize=(7.0, 1.95))
    draw_robustness(list(axs), [0, 1, 2, 3])
    fig.tight_layout(pad=0.2, w_pad=0.8)
    save(fig, "fig_robustness_wide.pdf")
    return {"figures": [os.path.relpath(x, os.path.join(HERE, "..")) for x in written]}


# =========================================================================== #
EXPERIMENTS = [
    ("R1", "R1_exact_validation.json", r1_validation),
    ("R2", "R2_frontiers.json", r2_frontiers),
    ("R3", "R3_budget_split.json", r3_budget),
    ("R4", "R4_strategic_censor.json", r4_strategic),
    ("R5", "R5_diversification.json", r5_diversification),
    ("R6", "R6_heavy_tail_discovery.json", r6_heavy_tail),
    ("R7", "R7_sync_discovery.json", r7_sync),
    ("R8", "R8_mint_exposure.json", r8_exposure),
    ("R9", "R9_range_blocking.json", r9_range),
    ("R10", "R10_perunit_normalization.json", r10_perunit),
    ("R11", "R11_profiles.json", r11_profiles),
    ("R13", "R13_rotation_speed.json", r13_rotation),
    ("FIG", "R12_figures.json", figures),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None,
                    help="comma-separated keys, e.g. R1,R2,FIG")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    timings = {}
    for key, fname, fn in EXPERIMENTS:
        if only and key not in only:
            continue
        print(f"[{key}] {fn.__name__} ...", flush=True)
        t0 = time.time()
        res = fn()
        res["_meta"] = _meta(t0)
        _save(fname, res)
        timings[key] = res["_meta"]["runtime_s"]
        print(f"    done in {timings[key]:.1f}s", flush=True)
    print("runtimes (s):", timings)


if __name__ == "__main__":
    main()
