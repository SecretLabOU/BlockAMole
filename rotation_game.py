"""
rotation_game.py -- Event-driven simulator for the moving-target rotation game.

This is the open "censor-defender simulator" (the rotation-game layer). It is a
continuous-time (Gillespie / next-event) Markov simulation of Definition 1 in the
paper.

Key structural fact (used for both clarity and speed): the game decomposes into
two *independent* birth-death layers.

  ADDRESS layer  -- num_clear(t) in {0,...,n}, the number of endpoints with a
      clear address.  block:  clear->blocked at total rate lam_a * num_clear
      recover: blocked->clear at total rate mu * (n - num_clear).
      The system is ADDRESS-DOWN while num_clear == 0.

  DOMAIN layer   -- K(t) in {0,...,kmax}, live unblocked registrable domains.
      birth (mint):  rate lam_intro while K < kmax
      death (burn):  rate lam_disc  while K >= 1.
      The system is DOMAIN-DOWN while K == 0.

The system is REACHABLE iff (num_clear >= 1) AND (K >= 1), so the set of
"down" intervals is the union of the two layers' down intervals. Because the
layers are independent, we simulate each as a cheap scalar birth-death chain
(batched RNG) and combine. This also lets sweeps reuse one address realization
across many domain settings (see run_experiments.py).

Metrics returned (post warm-up):
  time_avg_avail   -- fraction of time reachable
  interval_avail   -- P[a random window of length t_window is *entirely* up]
                      (the (alpha,T)-availability of Definition 2)
  mean_live_domains, p_pool_empty, ip_denial_emp  -- diagnostics
"""

from dataclasses import dataclass, asdict
import numpy as np

_CHUNK = 1 << 16


@dataclass
class GameParams:
    n: int = 8                # active endpoints (address redundancy)
    mu: float = 3.0           # per-endpoint rotation rate (IP / sub-domain)
    lam_a: float = 1.0        # per-endpoint address-discovery rate
    lam_intro: float = 1.0    # registrable-domain introduction rate (defender)
    lam_disc: float = 0.5     # registrable-domain burn rate (censor)
    kmax: int = 8             # defender domain buffer (max live unblocked domains)
    burn_batch: int = 1       # domains burned per discovery event (>1 = bursty)
    horizon: float = 15000.0  # simulated time (in 1/lam_intro units)
    warmup_frac: float = 0.1  # discard this leading fraction as transient
    t_window: float = 5.0     # T for the (alpha, T)-interval-availability metric

    @property
    def beta(self):
        return self.lam_disc / self.lam_intro


# --------------------------------------------------------------------------- #
#  Generic scalar birth-death simulator -> down-intervals where state == 0
# --------------------------------------------------------------------------- #
def _simulate_birth_death(birth_fn, death_fn, x0, hi, horizon, warmup, rng,
                          down_step=1):
    """Simulate a birth-death chain on {0,...,hi}; return down-intervals (x==0),
    fraction of post-warmup time at 0, and time-integral of x (for the mean).

    birth_fn(x), death_fn(x) return nonnegative rates for x->x+1 and a death
    transition x->max(0, x-down_step).  down_step>1 models bursty/correlated
    removals (e.g. a registrar takedown burning several domains at once).
    """
    t = 0.0
    x = x0
    down_intervals = []
    cur_down_start = x == 0 and warmup or None
    if x == 0:
        cur_down_start = max(0.0, warmup)
    zero_time = 0.0
    x_integral = 0.0
    # batched randoms
    ue = rng.random(_CHUNK)
    ub = rng.random(_CHUNK)
    idx = 0
    while t < horizon:
        if idx >= _CHUNK:
            ue = rng.random(_CHUNK)
            ub = rng.random(_CHUNK)
            idx = 0
        b = birth_fn(x)
        d = death_fn(x)
        R = b + d
        if R <= 0.0:
            break
        dt = -np.log(ue[idx]) / R
        t_next = t + dt
        # accumulate occupancy over [t, t_next) in the post-warmup region
        seg_lo = t if t > warmup else warmup
        seg_hi = t_next if t_next < horizon else horizon
        if seg_hi > seg_lo:
            seg = seg_hi - seg_lo
            x_integral += x * seg
            if x == 0:
                zero_time += seg
        t = t_next
        if t >= horizon:
            break
        # fire
        if ub[idx] * R < b:
            x += 1
        else:
            x -= down_step if x >= down_step else x
        idx += 1
        # track down (x==0) transitions, post-warmup
        if t >= warmup:
            if x == 0 and cur_down_start is None:
                cur_down_start = t
            elif x != 0 and cur_down_start is not None:
                down_intervals.append((cur_down_start, t))
                cur_down_start = None
    if cur_down_start is not None:
        down_intervals.append((cur_down_start, horizon))
    measured = max(horizon - warmup, 1e-12)
    return down_intervals, zero_time / measured, x_integral / measured


def simulate_address(p: GameParams, seed=0):
    """Address layer: returns (down_intervals, p_all_blocked)."""
    rng = np.random.default_rng(seed)
    n, mu, lam_a = p.n, p.mu, p.lam_a
    downs, p_zero, _ = _simulate_birth_death(
        birth_fn=lambda c: mu * (n - c),       # blocked -> clear
        death_fn=lambda c: lam_a * c,          # clear -> blocked
        x0=n, hi=n,
        horizon=p.horizon, warmup=p.warmup_frac * p.horizon, rng=rng)
    return downs, p_zero


def simulate_provider(lam_intro_p, lam_disc_p, kmax, horizon, warmup, seed=0):
    """One provider's domain pool where a takedown empties the whole pool.

    Models a correlated registrar/CA takedown: births at lam_intro_p (cap kmax),
    and each takedown (rate lam_disc_p) removes *all* live domains at once.
    Returns down-intervals where the provider has no live domain.
    """
    rng = np.random.default_rng(seed)
    downs, _, _ = _simulate_birth_death(
        birth_fn=lambda k: lam_intro_p if k < kmax else 0.0,
        death_fn=lambda k: lam_disc_p if k >= 1 else 0.0,
        x0=kmax, hi=kmax, horizon=horizon, warmup=warmup, rng=rng,
        down_step=kmax)            # a takedown empties the provider
    return downs


def _intersect_two(a, b):
    """Intersection of two sorted lists of (start, end) intervals."""
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if hi > lo:
            out.append((lo, hi))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def intersect(interval_lists):
    """Intersection across many interval lists (empty if any list is empty)."""
    if not interval_lists:
        return []
    acc = _merge(interval_lists[0])
    for lst in interval_lists[1:]:
        if not lst:
            return []
        acc = _intersect_two(acc, _merge(lst))
        if not acc:
            return []
    return acc


def simulate_domain(p: GameParams, seed=0):
    """Domain layer: returns (down_intervals, p_pool_empty, mean_live_domains).

    With burn_batch b>1, each burn removes b domains but fires at rate
    lam_disc/b, so the mean burn throughput (and hence beta) is unchanged; only
    the burst structure differs.
    """
    rng = np.random.default_rng(seed)
    li, kmax, b = p.lam_intro, p.kmax, p.burn_batch
    ld = p.lam_disc / b   # event rate; throughput b*ld = lam_disc, so beta fixed
    downs, p_zero, mean_k = _simulate_birth_death(
        birth_fn=lambda k: li if k < kmax else 0.0,
        death_fn=lambda k: ld if k >= 1 else 0.0,
        x0=kmax, hi=kmax,
        horizon=p.horizon, warmup=p.warmup_frac * p.horizon, rng=rng,
        down_step=b)
    return downs, p_zero, mean_k


# --------------------------------------------------------------------------- #
#  Combine two layers' down-intervals into the (alpha,T) interval metric
# --------------------------------------------------------------------------- #
def _merge(intervals):
    """Merge overlapping intervals; accepts lists or tuples, returns tuples."""
    if not intervals:
        return []
    intervals = sorted(tuple(iv) for iv in intervals)
    out = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def interval_up_probability(down_intervals, span_lo, span_hi, t_window):
    """P[a uniformly random window [t0,t0+T] in [span_lo, span_hi] is fully up].

    A window fails iff it intersects a down-interval [s,e]; offending starts are
    (s-T, e). Measure their union (clipped) and subtract from 1.
    """
    span = span_hi - span_lo - t_window
    if span <= 0:
        return float("nan")
    if not down_intervals:
        return 1.0
    bad = []
    for s, e in down_intervals:
        lo = max(span_lo, s - t_window)
        hi = min(span_lo + span, e)
        if hi > lo:
            bad.append((lo, hi))
    if not bad:
        return 1.0
    merged = _merge(bad)
    bad_len = sum(e - s for s, e in merged)
    return max(0.0, 1.0 - bad_len / span)


def combine(p: GameParams, addr_downs, addr_pzero, dom_downs, dom_pzero, dom_meank):
    """Assemble the full metric dict from the two simulated layers."""
    warmup = p.warmup_frac * p.horizon
    all_downs = _merge(list(addr_downs) + list(dom_downs))
    # time-average availability = fraction of post-warmup time with no down
    down_len = sum(e - s for s, e in all_downs)
    measured = max(p.horizon - warmup, 1e-12)
    time_avg = 1.0 - down_len / measured
    interval = interval_up_probability(all_downs, warmup, p.horizon, p.t_window)
    return {
        "time_avg_avail": time_avg,
        "interval_avail": interval,
        "mean_live_domains": dom_meank,
        "p_pool_empty": dom_pzero,
        "ip_denial_emp": addr_pzero,
        "beta": p.beta,
    }


def run_once(p: GameParams, seed=0):
    """Full joint realization (address + domain) -> metrics dict."""
    a_downs, a_pz = simulate_address(p, seed=2 * seed + 1)
    d_downs, d_pz, d_mk = simulate_domain(p, seed=2 * seed + 2)
    return combine(p, a_downs, a_pz, d_downs, d_pz, d_mk)


def run(p: GameParams, seeds=24):
    """Average metrics over `seeds` independent realizations."""
    rows = [run_once(p, seed=s) for s in range(seeds)]
    keys = [k for k in rows[0] if k != "beta"]
    out = {k: float(np.mean([r[k] for r in rows])) for k in keys}
    out["beta"] = p.beta
    out["interval_avail_std"] = float(np.std([r["interval_avail"] for r in rows]))
    out["time_avg_avail_std"] = float(np.std([r["time_avg_avail"] for r in rows]))
    out["params"] = asdict(p)
    return out


if __name__ == "__main__":
    for b in (0.3, 0.6, 0.9, 1.0, 1.2, 1.6):
        p = GameParams(lam_disc=b)
        m = run(p, seeds=12)
        print(f"beta={b:>4}  time_avg={m['time_avg_avail']:.3f}  "
              f"interval={m['interval_avail']:.3f}  "
              f"meanK={m['mean_live_domains']:.2f}  "
              f"P[empty]={m['p_pool_empty']:.3f}  "
              f"ip_denial={m['ip_denial_emp']:.2e}")
