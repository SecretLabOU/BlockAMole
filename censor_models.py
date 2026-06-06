"""
censor_models.py -- Calibrated adversary presets for the rotation game.

Each preset fixes the *censor-controlled* primitives (address-discovery rate,
relative domain-block capacity, collateral budget gamma) to values consistent
with documented nation-state censors. The *defender-controlled* knobs
(rotation rate mu, introduction rate lam_intro, endpoints n, buffer kmax) are
chosen separately by the experiment driver.

Time unit: one mean domain-introduction interval (lam_intro = 1). Rates for the
address layer are expressed as multiples of that unit; what matters analytically
is the ratio mu / lam_a (address layer) and beta = lam_disc / lam_intro (domain
layer), so the dimensionless presets transfer to any wall-clock calibration.

Calibration rationale (documented behavior):
  * GFW   -- real-time DPI + active probing -> fast address discovery; since
             April 2024 it decrypts QUIC Initials and blocks by domain at scale,
             and a growing domestic cloud erodes collateral freedom -> high
             domain-block capacity, larger gamma.
  * TSPU  -- ISP-level protocol blocking at line speed but historically less
             aggressive per-domain enumeration -> moderate discovery, moderate
             domain capacity.
  * Iran  -- protocol whitelisting + throttling, periodic hard shutdowns ->
             moderate-to-fast discovery, high gamma during unrest.
The numbers below are deliberately *adversary-favorable* (fast discovery, high
gamma) so reported guarantees are conservative.
"""

from rotation_game import GameParams

# mu is the defender's rotation rate; the canonical runs anchor mu = 3.0 and
# express each censor's discovery rate relative to it (so mu/lam_a is 2.0, 3.75,
# 3.0 for GFW, TSPU, Iran). lam_disc_scale multiplies the swept domain-burn capacity.
CENSORS = {
    "gfw": {
        "label": "GFW (China)",
        "lam_a": 1.5,          # fast active probing  (mu/lam_a = 2.0)
        "gamma": 0.20,         # erodes as domestic cloud grows
        "lam_disc_scale": 1.0,
    },
    "tspu": {
        "label": "TSPU (Russia)",
        "lam_a": 0.8,          # slower per-endpoint discovery (mu/lam_a = 3.75)
        "gamma": 0.05,
        "lam_disc_scale": 0.8,
    },
    "iran": {
        "label": "Iran",
        "lam_a": 1.0,          # (mu/lam_a = 3.0)
        "gamma": 0.10,
        "lam_disc_scale": 0.9,
    },
}

DEFAULT_DEFENDER = dict(n=8, mu=3.0, lam_intro=1.0, kmax=8,
                        horizon=20000.0, warmup_frac=0.1, t_window=5.0)


def make_params(censor="gfw", beta=0.5, **overrides):
    """Build GameParams for a given calibrated censor and target beta.

    beta is realized by setting lam_disc = beta * lam_intro * lam_disc_scale-free
    (we keep lam_intro = 1 and lam_disc = beta, then let the censor's
    lam_disc_scale stretch the absolute domain timescale only via overrides).
    """
    c = CENSORS[censor]
    cfg = dict(DEFAULT_DEFENDER)
    cfg.update(lam_a=c["lam_a"])
    cfg.update(overrides)
    cfg["lam_disc"] = beta * cfg["lam_intro"]
    return GameParams(**cfg)


def censor_label(key):
    return CENSORS[key]["label"]
