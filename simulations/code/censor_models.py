"""
censor_models.py -- Illustrative adversary presets (GFW-, TSPU- and Iran-like
operating points); they are not fitted to any censor.

Each preset fixes the *censor-controlled* rates: the per-endpoint
address-discovery rate lam_a, plus a name-burn scale lam_disc_scale and a
collateral budget gamma. The labels name the censors that motivated each
operating point, but the values are not measurements. The experiments use only
lam_a and the label; gamma and lam_disc_scale are not used by any experiment.
The *defender-controlled* knobs (rotation rate mu, mint rate lam_intro,
endpoints n, buffer kmax) are chosen separately by the experiment driver.

Time unit: one mean mint interval (lam_intro = 1). Address-layer rates are
multiples of that unit. For given n and kmax, time-average availability
depends on the rates only through mu / lam_a (address layer) and
beta = lam_disc / lam_intro (name layer). Interval availability also depends on
the window length T: through lam_a * T in the address layer and
lam_intro * T in the name layer.
"""

from rotation_game import GameParams

# The canonical runs fix the defender's rotation rate at mu = 3.0, so the
# presets give mu/lam_a = 2.0, 3.75 and 3.0.
CENSORS = {
    "gfw": {
        "label": "GFW (China)",
        "lam_a": 1.5,          # mu/lam_a = 2.0
        "gamma": 0.20,
        "lam_disc_scale": 1.0,
    },
    "tspu": {
        "label": "TSPU (Russia)",
        "lam_a": 0.8,          # mu/lam_a = 3.75
        "gamma": 0.05,
        "lam_disc_scale": 0.8,
    },
    "iran": {
        "label": "Iran",
        "lam_a": 1.0,          # mu/lam_a = 3.0
        "gamma": 0.10,
        "lam_disc_scale": 0.9,
    },
}

DEFAULT_DEFENDER = dict(n=8, mu=3.0, lam_intro=1.0, kmax=8,
                        horizon=20000.0, warmup_frac=0.1, t_window=5.0)


def make_params(censor="gfw", beta=0.5, **overrides):
    """Build GameParams for a given preset and target beta.

    Sets lam_disc = beta * lam_intro after applying any overrides; the
    preset's lam_disc_scale is not applied.
    """
    c = CENSORS[censor]
    cfg = dict(DEFAULT_DEFENDER)
    cfg.update(lam_a=c["lam_a"])
    cfg.update(overrides)
    cfg["lam_disc"] = beta * cfg["lam_intro"]
    return GameParams(**cfg)


def censor_label(key):
    return CENSORS[key]["label"]
