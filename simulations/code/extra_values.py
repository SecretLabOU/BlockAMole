#!/usr/bin/env python3
"""
extra_values.py -- paper values that no result file stores.

Short exact computations with exact.py. The script reads no result file, writes
nothing and runs in about three seconds.

  Figure 2     interval availability A_5 at beta = 2 for each plotted buffer
  Section 5.3  the address window W_T^addr at n = 8 and mu/lambda_a = 1 for
               lambda_a T = 5, 15 and 60; the value at lambda_a T = 5 repeats
               R13_rotation_speed.json
  Section 5.3  the exact thresholds of mu/lambda_a at which beta* comes within
               0.01 of its value for a perfect address layer, next to the grid
               values that R13_rotation_speed.json stores
  Section 5.3  wall-clock timescales: the smallest mu/lambda_a with
               W_T^addr >= 0.95 for a one-hour (lambda_a T = 60) and a one-day
               (lambda_a T = 1440) session at a mean time to block of one
               minute, and the implied time between rotations of an endpoint
  Section 7    the time to compute one exact interval frontier at k_max = 8
               (step 3; machine-dependent)
  Appendix B   the closed-form address bound after Corollary B.2,
               1 - p^n (1 + n mu T), against the exact W_5^addr
  Appendix B   the single-crossing grid check (exact.check_single_crossing)
               of the frontiers of Section 5.4 and Appendix C that the result
               files store without one: bursts of b = 2, 4 and 8 names, the
               strike-all censor against a reserve of r = 1, 2 and 4 names, and
               the strike-all time-average frontiers at k_max = 8 and 32
  Appendix C   the bound (1 - rho) beta*(0.95, 5) at k_max = 8
  Appendix C   per-name discovery at k_max = 8, where the censor finds each
               live name at rate delta and so burns at rate delta K: the
               largest delta that meets the target (0.95, 5), Pr[K >= 1] and
               the names burned per mint interval there, overall and while a
               name is live (the rate that step 7 of Section 7 estimates),
               against the constant-rate beta*(0.95, 5), that rate as
               Pr[K < k_max] / Pr[K >= 1] by flow balance, and the delta at
               which it equals beta*, with A_5 there.
               R10_perunit_normalization.json stores delta, Pr[K = 0] and the
               overall burns at that frontier (results["8"]["delta=lam_disc"])

`python3 exact.py` prints the accuracy figures of Appendix B.

Run:  python3 extra_values.py
"""

import os
import sys
import timeit

sys.dont_write_bytecode = True          # keep __pycache__ out of simulations/code
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                      # noqa: E402
from scipy.optimize import brentq       # noqa: E402

import exact as ex                      # noqa: E402

# canonical configuration; time unit 1/lam_intro = 1/lam_a
N, LAM_A, MU, KMAX, T5, ALPHA = 8, 1.0, 3.0, 8, 5.0, 0.95


def main():
    a5 = ex.addr_window(N, LAM_A, MU, T5)
    vals = ", ".join(f"k_max = {k}: {ex.name_window_constant(2.0, k, T5) * a5:.3f}"
                     for k in (4, 8, 16, 32, 64))
    print("Figure 2, interval availability A_5 at beta = 2:")
    print(f"  {vals}")

    print("Section 5.3, address window W_T^addr at n = 8 (lambda_a = 1, so T = lambda_a T):")
    for lat in (5.0, 15.0, 60.0):
        w = ex.addr_window(N, LAM_A, LAM_A, lat)
        print(f"  mu/lambda_a = 1, lambda_a T = {lat:g}: {w:.3f}")

    # R13 stores the smallest mu/lambda_a on its grid from which beta* stays
    # within TOL of its value for a perfect address layer (mu -> infinity).
    # beta* rises with mu/lambda_a, so the exact threshold lies between the grid
    # value and the grid point below it.
    grid, tol = np.geomspace(0.5, 128.0, 49), 0.01
    lim_i = ex.beta_star(lambda b: ex.name_window_constant(b, KMAX, T5), ALPHA)[0]
    lim_a = ex.beta_star(lambda b: 1.0 - ex.pi0_geometric(b, KMAX), ALPHA)[0]

    def gap_interval(x, la):
        v = ex.frontier_interval(ALPHA, T5, N, la, x * la, KMAX)[0]
        return (-1.0 if v is None else v) - (lim_i - tol)

    def gap_timeavg(x):
        v = ex.frontier_timeavg(ALPHA, N, LAM_A, x * LAM_A, KMAX)[0]
        return (-1.0 if v is None else v) - (lim_a - tol)

    print("Section 5.3, mu/lambda_a at which beta* comes within 0.01 of its limit "
          "(n = 8, k_max = 8), exact and on the grid of R13:")
    cases = [(f"interval, lambda_a T = {la * T5:g}", lambda x, la=la: gap_interval(x, la))
             for la in (1.0, 10.0, 60.0)] + [("time average", gap_timeavg)]
    for label, gap in cases:
        i = next(i for i, x in enumerate(grid) if gap(x) >= 0.0)
        root = brentq(gap, grid[i - 1], grid[i], xtol=1e-10)
        print(f"  {label}: {root:.3f}, grid {grid[i]:.3f} "
              f"({100.0 * (grid[i] / root - 1.0):.1f}% above)")

    print("Section 5.3, smallest mu/lambda_a with W_T^addr >= 0.95 "
          "(mean time to block one minute):")
    for lat, session in ((60.0, "one-hour session"), (1440.0, "one-day session")):
        r = brentq(lambda x: ex.addr_window(N, LAM_A, x, lat) - ALPHA, 1.0, 20.0,
                   xtol=1e-10)
        print(f"  {session} (lambda_a T = {lat:g}): mu/lambda_a = {r:.2f}, "
              f"one rotation every {60.0 / r:.0f} s per endpoint")

    frontier = lambda: ex.frontier_interval(ALPHA, T5, N, LAM_A, MU, KMAX)  # noqa: E731
    best = min(timeit.repeat(frontier, number=20, repeat=5)) / 20
    print(f"Section 7, one exact interval frontier at k_max = 8: {1000 * best:.1f} ms "
          "(best of 5 x 20 runs; machine-dependent)")

    p = LAM_A / (LAM_A + MU)
    bound = 1.0 - p ** N * (1.0 + N * MU * T5)
    print("Appendix B, closed-form address bound after Corollary B.2 (n = 8, mu = 3, T = 5):")
    print(f"  1 - p^n (1 + n mu T) = {bound:.5f}; exact W_5^addr = {a5:.5f}")

    print("Appendix B, single-crossing grid check of the frontiers of Section 5.4 "
          "and Appendix C that no result file checks:")
    chains = ([(f"bursts, b = {b}", ex.batch_name_chain(KMAX, b)) for b in (2, 4, 8)]
              + [(f"strike-all with reserve, r = {r}", ex.strategic_chain(KMAX, "strike_all", r=r))
                 for r in (1, 2, 4)])
    for label, chain in chains:
        avail = lambda x, ch=chain: ch.window(T5, intro=1.0, disc=x) * a5  # noqa: E731
        root, _ = ex.beta_star(avail, ALPHA)
        print(f"  {label}: beta* = {root:.3f}, single crossing: "
              f"{ex.check_single_crossing(avail, ALPHA, root)}")
    ca = ex.addr_timeavg(N, LAM_A, MU)
    for k in (8, 32):
        chain = ex.strategic_chain(k, "strike_all", r=0)
        avail = lambda x, ch=chain: ch.timeavg(intro=1.0, disc=x) * ca  # noqa: E731
        root, _ = ex.beta_star(avail, ALPHA)
        print(f"  strike-all, time average, k_max = {k}: beta*_avg = {root:.3f}, "
              f"single crossing: {ex.check_single_crossing(avail, ALPHA, root)}")

    bstar, _ = frontier()
    print(f"Appendix C, bound (1 - rho) beta* at k_max = 8 (beta*(0.95, 5) = {bstar:.3f}):")
    print("  " + ", ".join(f"rho = {rho:g}: {(1.0 - rho) * bstar:.3f}"
                           for rho in (0.25, 0.5, 0.75, 0.9)))

    # Per-name discovery: the pool is the birth-death chain with death rate
    # delta k in state k (exact.name_rates_perunit). A larger delta raises every
    # death rate, so A_5 falls with delta (Lemma A.2) and the root is the
    # frontier without a single-crossing check.
    per_name = lambda d: ex.name_window_perunit(d, KMAX, T5) * a5  # noqa: E731
    dstar, _ = ex.beta_star(per_name, ALPHA)

    def pool(d):
        """Pr[K >= 1] and Pr[K < k_max] of the stationary pool, the names
        burned per mint interval (delta E[K]) and per mint interval while a
        name is live."""
        b, dth = ex.name_rates_perunit(KMAX, 1.0, d)
        pi = ex.bd_stationary(b, dth)
        burned = d * float(pi @ np.arange(KMAX + 1))
        return 1.0 - pi[0], 1.0 - pi[KMAX], burned, burned / (1.0 - pi[0])

    live, admitted, burned, rate = pool(dstar)
    # By flow balance the burns per mint interval equal the admitted mints,
    # Pr[K < k_max], so the rate is also Pr[K < k_max] / Pr[K >= 1], which the
    # line "by flow balance" prints without counting burns. The rate is
    # delta E[K | K >= 1] >= delta, so it exceeds beta* for every
    # delta > beta*, and a rate that rises on (0, beta*] makes the root unique.
    deltas = np.linspace(0.001, bstar, 400)
    rising = bool(np.all(np.diff([pool(d)[3] for d in deltas]) > 0))
    d_eq = brentq(lambda d: pool(d)[3] - bstar, 1e-6, dstar, xtol=1e-12)
    print("Appendix C, per-name discovery at k_max = 8 (the censor burns at rate delta K):")
    print(f"  the target (0.95, 5) holds up to delta = {dstar:.3f} per mint interval, where "
          f"Pr[K >= 1] = {live:.3f} and the censor burns {burned:.3f} names per mint interval")
    print(f"  there it burns {rate:.3f} names per mint interval while a name is live (the rate "
          f"that step 7 of Section 7 estimates), against beta* = {bstar:.3f} for a "
          f"constant-rate censor")
    print(f"  by flow balance that rate is Pr[K < k_max] / Pr[K >= 1] = {admitted:.3f} / "
          f"{live:.3f} = {admitted / live:.3f}")
    print(f"  that rate rises with delta up to beta* (grid check: {rising}) and equals "
          f"beta* = {bstar:.3f} at delta = {d_eq:.4f}, where A_5 = {per_name(d_eq):.3f}")


if __name__ == "__main__":
    main()
