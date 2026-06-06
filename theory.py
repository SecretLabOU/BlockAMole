"""
theory.py -- Closed-form predictions for the moving-target rotation game.

These functions implement the analytical results of the paper (Section: "The
Sustainability Frontier"). They are intentionally dependency-light (numpy only)
so they can be reused both by the figure scripts and by anyone re-deriving the
bounds.

Model recap (see paper Section 4-5):
  * n            active endpoints, each with an (address, domain) pair.
  * mu           per-endpoint rotation rate (refreshes the IP / sub-domain;
                 cheap, so it can be large).
  * lam_a        per-endpoint address-discovery rate (censor finds & blocks IP).
  * lam_intro    rate at which the defender mints fresh *registrable* domains
                 (costly -> the binding knob).
  * lam_disc     rate at which the censor discovers & persistently blocks
                 registrable domains.
  * beta         = lam_disc / lam_intro  (the dimensionless "domain burn rate").
  * kmax         defender's domain buffer: max # of fresh unblocked registrable
                 domains held live at once (a cost/stockpile knob).

Two decoupled layers:
  (Address layer) Each endpoint's IP is a 2-state CTMC: clear ->(lam_a) blocked,
      blocked ->(mu) clear. Stationary P[IP blocked] = lam_a/(lam_a+mu).
      With n independent endpoints, P[all IPs blocked] = (lam_a/(lam_a+mu))^n.
  (Domain layer) The count K of live unblocked registrable domains is a
      birth-death chain on {0,...,kmax}: birth lam_intro (K<kmax), death lam_disc
      (K>=1). Detailed balance gives pi_k proportional to (1/beta)^k.

The system is reachable iff (K>=1) AND (at least one IP is clear), so the
stationary availability factorizes (Theorem: closed-form availability).
"""

import numpy as np


# --------------------------------------------------------------------------- #
#  Address layer (Lemma: the geometric IP bound)
# --------------------------------------------------------------------------- #
def p_ip_blocked(lam_a, mu):
    """Stationary probability a single endpoint's address is blocked."""
    return lam_a / (lam_a + mu)


def ip_denial(n, lam_a, mu):
    """P[all n endpoints' addresses blocked] = (lam_a/(lam_a+mu))^n.

    This is the worst case for the defender (every discovered address blocked
    instantly, ignoring the collateral cap gamma), so the realized value is an
    upper bound. It decays geometrically in n -> address blocking is a losing
    strategy for the censor.
    """
    return p_ip_blocked(lam_a, mu) ** n


def ip_availability(n, lam_a, mu):
    """P[at least one endpoint has a clear address]."""
    return 1.0 - ip_denial(n, lam_a, mu)


# --------------------------------------------------------------------------- #
#  Domain layer (birth-death pool)
# --------------------------------------------------------------------------- #
def pool_empty_prob(beta, kmax):
    """Stationary P[K = 0] for the capped birth-death domain pool.

    pi_k proportional to (1/beta)^k on {0,...,kmax}, so
        pi_0 = (1 - r) / (1 - r^{kmax+1}),   r = 1/beta.
    For beta == 1 the chain is uniform and pi_0 = 1/(kmax+1).
    """
    beta = float(beta)
    if abs(beta - 1.0) < 1e-12:
        return 1.0 / (kmax + 1.0)
    r = 1.0 / beta
    return (1.0 - r) / (1.0 - r ** (kmax + 1))


def pool_nonempty_prob(beta, kmax):
    """Stationary P[K >= 1] (a usable domain exists)."""
    return 1.0 - pool_empty_prob(beta, kmax)


# --------------------------------------------------------------------------- #
#  Combined stationary availability (the closed-form law)
# --------------------------------------------------------------------------- #
def stationary_availability(beta, n, lam_a, mu, kmax):
    """Closed-form time-average availability A(beta, n, mu, lam_a, kmax).

    A = P[K>=1] * P[>=1 clear address]
      = (1 - pi_0(beta, kmax)) * (1 - (lam_a/(lam_a+mu))^n).
    """
    return pool_nonempty_prob(beta, kmax) * ip_availability(n, lam_a, mu)


def beta_star_timeavg(alpha, n, lam_a, mu, kmax,
                      lo=1e-3, hi=10.0, tol=1e-6):
    """Largest beta with stationary availability >= alpha (time-average sense).

    Returns np.nan if even beta -> 0 cannot reach alpha (address layer too weak).
    Availability is monotone decreasing in beta, so we bisect.
    """
    a_lo = stationary_availability(lo, n, lam_a, mu, kmax)
    if a_lo < alpha:
        return np.nan  # address layer alone cannot deliver alpha
    a_hi = stationary_availability(hi, n, lam_a, mu, kmax)
    if a_hi >= alpha:
        return hi
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if stationary_availability(mid, n, lam_a, mu, kmax) >= alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------- #
#  Domain-economy calculator (operational recipe)
# --------------------------------------------------------------------------- #
def min_intro_rate(lam_disc, beta_target):
    """Minimum domain-introduction rate to hold beta <= beta_target.

    beta = lam_disc / lam_intro <= beta_target  <=>  lam_intro >= lam_disc/beta_target.
    """
    return lam_disc / beta_target


def domains_per_day(lam_intro_per_hr):
    """Convert an introduction rate (per hour) to fresh domains per day."""
    return lam_intro_per_hr * 24.0


def daily_cost(lam_intro_per_hr, cost_per_domain):
    """Rough operating cost per day for the domain economy."""
    return domains_per_day(lam_intro_per_hr) * cost_per_domain


if __name__ == "__main__":
    # Tiny self-check / sanity print.
    print("IP denial (n=5, lam_a=mu):", ip_denial(5, 1.0, 1.0))
    for b in (0.5, 0.9, 1.0, 1.1, 2.0):
        print(f"beta={b:>4}: P[pool nonempty]={pool_nonempty_prob(b, 8):.4f}, "
              f"A={stationary_availability(b, 6, 0.5, 1.0, 8):.4f}")
    print("beta* (alpha=0.95, n=6):",
          beta_star_timeavg(0.95, 6, 0.5, 1.0, 8))
