"""
run_experiments.py -- Drive the event-driven simulation experiments E1-E10 and
dump results.

Writes one JSON per experiment into ../results/. exact_experiments.py (R1)
compares every file with the exact solver, and paper/figures/make_figures.py
plots the E2 simulations in Figure 2. A full run takes about one hour on one
core.

The model assumes that the address and domain (name) layers are independent
(see rotation_game.py), so sweeps reuse one address realization across many
domain settings (and vice versa), which is the bulk of the speedup.

Experiments
  E1  ip_geometric      P[all n addresses blocked] vs n, simulation vs closed form
  E2  phase_transition  the sustainability frontier (interval availability vs beta)
  E3  mu_heatmap        availability over beta x mu/lam_a (both metrics)
  E4  beta_star_grid    closed-form time-average beta*(n, kmax) at the illustrative presets
  E5  domain_economy    operating recipe: required intro rate vs censor burn rate
  E6-E10                session length, bursty burns, budget split, providers,
                        discovery model (see each function)

The exact solver (exact.py, exact_experiments.py) recomputes these results
(R1). For providers the paper reports the pooled model of R5, not E9. The
paper uses E8 and E9 only through the R1 comparison.

Run:  python3 run_experiments.py [--quick] [--only E2,E7]
"""

import argparse
import json
import os
import time

import numpy as np

import theory
from rotation_game import (GameParams, run, simulate_address, simulate_domain,
                           simulate_provider, combine, interval_up_probability,
                           intersect, _merge, _simulate_birth_death)
from censor_models import CENSORS

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# canonical defender configuration (strong address layer -> domain layer binds)
N, MU, LAM_A, KMAX = 8, 3.0, 1.0, 8


def _save(name, obj):
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"  -> wrote {os.path.relpath(path)}")


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


# --------------------------------------------------------------------------- #
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
    """E2: interval availability vs beta for several domain buffers kmax.

    Reuses one address realization per seed across all (beta, kmax)."""
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
    """E3: time-average and interval availability over a (beta, mu/lam_a) grid.

    Reuses address realizations across beta and domain realizations across mu."""
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
    """E4: closed-form time-average beta*(n, kmax) for each illustrative preset."""
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
    """E5: required introduction rate vs censor domain-block rate.

    Uses the simulated interval beta* (a grid value) at the canonical config,
    then maps a censor burn rate (units/day) to the minimum mint rate
    burn / beta* that keeps beta below the frontier."""
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
    # USD per unit. This fits labels under an owned domain or platform tenant
    # names, not registrable domains (the cheapest cost $1.54 for the first
    # year at one registrar's list prices in October 2026; see the paper).
    cost_per_domain = 0.01
    daily_cost = [r * cost_per_domain for r in required_intro]
    return {"alpha": alpha, "beta_star_interval": bstar, "kmax": KMAX,
            "betas": betas, "interval": iv,
            "burn_per_day": burn_per_day, "required_intro_per_day": required_intro,
            "cost_per_domain": cost_per_domain, "daily_cost": daily_cost}


def exp_session_length(seeds, quick):
    """E6: the interval frontier beta*(alpha,T) vs session length T.

    Many window lengths T are evaluated from the *same* simulated excursion
    structure (essentially free). We use a fine beta grid so the extracted
    frontier beta*(alpha,T) is smooth, a dense (log-spaced) set of T for the
    frontier curve, and a small subset of T for the readable left-panel curves.
    """
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


def exp_budget_allocation(seeds, quick):
    """E8: the censor's budget split B = n*lam_a + lam_disc at B = 1.5.

    A fraction f of the budget goes to names, lam_disc = f*B (aggregate), and
    the rest is spread over n endpoints, lam_a = (1-f)*B/n. Availability is
    simulated on a grid of f up to 0.97. The exact counterpart is R3
    (exact_experiments.py), which finds the censor's optimum at a corner
    (f = 0 or f = 1) in all configurations it tests, including these."""
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
        fstar = fracs[int(np.argmin(iv))]   # best value on the grid (ends at 0.97)
        out["curves"][str(n)] = {"interval": iv, "f_star": fstar}
    return out


def exp_multiprovider(seeds, quick):
    """E9: names spread over P providers with idle per-provider clocks.

    Nominal minting and takedown rates are split equally over P providers, and
    a takedown empties an entire provider's pool (a correlated registrar/CA
    takedown). The system is up iff >=1 provider has a live domain. A
    provider's takedown clock idles while its pool is empty, so the realized
    burn rate falls below lam_disc. The model therefore describes
    provider-initiated suspensions at fixed per-provider rates, not a censor
    with full takedown capacity. The paper uses the pooled model of R5
    (exact_experiments.py), whose frontier never exceeds the single pool's."""
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


def exp_bursty_burns(seeds, quick):
    """E7: correlated (bursty) burns of b names at a fixed mean burn rate."""
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


def exp_discovery_robustness(seeds, quick):
    """E10: constant-rate vs per-unit discovery, and E9's provider law.

    Part A contrasts the paper's constant aggregate burn rate lam_disc with
    *per-unit* discovery, where the censor blocks each live unit independently at
    rate delta so the aggregate burn is delta*K, matched at the full pool
    (delta*kmax = lam_disc). The pool is then a truncated-Poisson chain whose
    burn never exceeds lam_disc, so it is more available than the constant-rate
    pool. The direction of the comparison depends on this matching; R10 gives
    two other normalizations.

    Part B checks the law A_P = 1 - q^P for P independent provider pools
    (q = per-provider empty fraction) under E9's idle per-provider clocks,
    where independence makes it hold by construction; the paper uses the
    pooled model of R5 instead."""
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
    "E1_ip_geometric.json": exp_ip_geometric,
    "E2_phase_transition.json": exp_phase_transition,
    "E3_mu_heatmap.json": exp_mu_heatmap,
    "E4_beta_star_grid.json": exp_beta_star_grid,
    "E5_domain_economy.json": exp_domain_economy,
    "E6_session_length.json": exp_session_length,
    "E7_bursty_burns.json": exp_bursty_burns,
    "E8_budget_allocation.json": exp_budget_allocation,
    "E9_multiprovider.json": exp_multiprovider,
    "E10_discovery_robustness.json": exp_discovery_robustness,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="smaller sweeps / shorter horizons for a fast run")
    ap.add_argument("--only", default=None,
                    help="comma-separated experiment keys, e.g. E2,E3")
    args = ap.parse_args()
    seeds = 12 if args.quick else 24

    only = set(args.only.split(",")) if args.only else None
    for name, fn in EXPERIMENTS.items():
        key = name.split("_")[0]
        if only and key not in only and name not in only:
            continue
        print(f"[{key}] {fn.__name__} ...", flush=True)
        t0 = time.time()
        result = fn(seeds, args.quick)
        result["_meta"] = {"seeds": seeds, "quick": args.quick,
                           "runtime_s": round(time.time() - t0, 1)}
        _save(name, result)
        print(f"    done in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
