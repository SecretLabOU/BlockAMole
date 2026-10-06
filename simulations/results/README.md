# Result files of the simulator and the exact solver

This directory holds the 23 result files behind the paper's model results. The
event-driven simulator wrote E1 to E10 and the exact solver wrote R1 to R13
(R12 is written by the step called FIG). They are computed results and contain
no third-party data. The code in `../code` recreates all of them offline. The
result files are licensed CC BY 4.0.

Commands run in `simulations/code` unless stated otherwise. Section numbers
refer to the paper, and the reference workstation is the 20-core Linux
workstation of its Appendix E.

## The files

| file | written by | runtime of the shipped run (s) | used in the paper |
|---|---|---|---|
| `E1_ip_geometric.json` | `python3 run_experiments.py --only E1` | 218.9 | implementation check of Appendix B (through R1) |
| `E2_phase_transition.json` | `python3 run_experiments.py --only E2` | 578.6 | markers and error bars of Figure 2, and the 148-point sweep of Appendix B (through R1) |
| `E3_mu_heatmap.json` | `python3 run_experiments.py --only E3` | 232.1 | the largest difference between simulation and exact solver, 0.0086 ("to within 0.009 elsewhere", Section 5.2 and Appendix B, through R1) |
| `E4_beta_star_grid.json` to `E10_discovery_robustness.json` | `python3 run_experiments.py --only E4` (and so on) | 0.0, 589.6, 315.0, 246.3, 607.3, 333.5, 235.2 | implementation check of Appendix B (through R1) |
| `R1_exact_validation.json` | `python3 exact_experiments.py --only R1` | 1.9 | implementation check (Section 5.2 and Appendix B), burst frontiers (Section 5.4), checks of Figure 2 |
| `R2_frontiers.json` | `python3 exact_experiments.py --only R2` | 60.89 | abstract, Sections 1, 5.2 and 5.4, Figure 1, checks of Figure 2 |
| `R3_budget_split.json` | `python3 exact_experiments.py --only R3` | 62.43 | not reported in the paper |
| `R4_strategic_censor.json` | `python3 exact_experiments.py --only R4` | 44.13 | strategic block timing (Sections 1, 5.4 and 8, Appendix C), the values at beta = 1 in Section 5.2 |
| `R5_diversification.json` | `python3 exact_experiments.py --only R5` | 22.54 | diversification (Section 5.4), Monte Carlo check (Appendix C) |
| `R6_heavy_tail_discovery.json` | `python3 exact_experiments.py --only R6` | 5.93 | Remark B.1 on general discovery delays (cited in Section 4) |
| `R7_sync_discovery.json` | `python3 exact_experiments.py --only R7` | 19.19 | Remark 4.4 on synchronized discovery, Monte Carlo check (Appendix C) |
| `R8_mint_exposure.json` | `python3 exact_experiments.py --only R8` | 26.9 | mint-time exposure (Section 5.4, Appendix C) |
| `R9_range_blocking.json` | `python3 exact_experiments.py --only R9` | 40.55 | not reported in the paper |
| `R10_perunit_normalization.json` | `python3 exact_experiments.py --only R10` | 0.31 | per-name discovery (Appendix C) |
| `R11_profiles.json` | `python3 exact_experiments.py --only R11` | 0.62 | not reported in the paper |
| `R12_figures.json` | `python3 exact_experiments.py --only FIG` | 6.29 | not reported in the paper (lists the auxiliary figures that FIG writes to `../figures_exact/`) |
| `R13_rotation_speed.json` | `python3 exact_experiments.py --only R13` | 9.06 | rotation speed (Sections 5.3 and 9), and the check of Theorem 5.3 in n and mu (Section 5.2 and Appendix A) |

- The ten simulations take about one hour on one core (their runtimes sum to
  3,356 s). `run_experiments.py` without `--only` runs all ten.
- The exact suite takes about five minutes of wall time on a 20-core
  workstation, because its Monte Carlo cross-checks run one process per core.
  Appendix E reports 302 s, and the runtimes of the 13 R files sum to 300.7 s.
  `exact_experiments.py` without `--only` runs all of R1 to R13 and FIG, in
  that order.
- R1 reads all ten E files, so the E files must exist before R1 runs. FIG reads
  E2, E7, R2, R4, R5 and R8.
- Appendix E counts the 12,248 numbers in the 13 R files. These are their
  numeric values other than booleans and `_meta.runtime_s`. The comparison
  under "Rerun and compare" prints 12,238 of them, because it reports the 10
  file sizes in R1's `inputs` separately.
- E3 averages `max(8, seeds // 2)` = 12 seeds per point, although its
  `_meta.seeds` records the run setting, 24. This is the 12 in Appendix E's
  "12 to 24 independent seeds".

## Provenance and hash lock

Each E file records `_meta` = {`seeds`, `quick`, `runtime_s`}. The seeds of
every run are fixed in `run_experiments.py`. Each R file records in `_meta`
its runtime, a UTC timestamp (`generated_utc`), the Python, NumPy and SciPy
versions, the configuration, and the SHA-256 of `exact.py` and
`exact_experiments.py` (`code_sha256`). R1 also records the SHA-256 and size of
each E file it read (`inputs`).

These records tie the files together. Editing `exact.py` or
`exact_experiments.py` breaks the `code_sha256` of all 13 R files, and
replacing an E file with a rerun breaks R1's `inputs`, because a rerun records
its own `runtime_s` (only E4, which runs in 0.0 s, comes out identical). Keep
the shipped files unchanged and compare reruns in a copy (see below). This check, run from the repository root, confirms the
records.

```bash
python3 - <<'EOF'
import hashlib, json, os

res = "simulations/results"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
code = {f: sha(f"simulations/code/{f}") for f in ("exact.py", "exact_experiments.py")}
bad = [n for n in sorted(os.listdir(res)) if n.startswith("R") and n.endswith(".json")
       and json.load(open(f"{res}/{n}"))["_meta"]["code_sha256"] != code]
inputs = json.load(open(f"{res}/R1_exact_validation.json"))["inputs"]
bad += [n for n, v in inputs.items()
        if v != {"sha256": sha(f"{res}/{n}"), "bytes": os.path.getsize(f"{res}/{n}")}]
print("mismatch:", bad if bad else "none (13 R files match the code, R1 matches the 10 E files)")
EOF
```

Expected output:

```
mismatch: none (13 R files match the code, R1 matches the 10 E files)
```

SHA-256 of the shipped files, checked from the repository root. On macOS,
use `shasum -a 256 -c` instead of `sha256sum -c`.

```bash
sha256sum -c <<'EOF'
9a24fccfbe8e2ac2abb4c00d365f73e9967d8aead2ee6fea602fad31bd3ef4c4  simulations/results/E1_ip_geometric.json
bb66c89bf144c5116871f1a857e9bc00612e33d717b4833891469514299a5e04  simulations/results/E2_phase_transition.json
70fc7520bc2f2a1d9b681537a7884f7ff221e6810a61f45061e40471c4aec6aa  simulations/results/E3_mu_heatmap.json
f35faffb13d392792ad3802875b4bda672f6a90c1da6f6eaa6996da29c4415ed  simulations/results/E4_beta_star_grid.json
61beb156a60782bffeb3f15bf398a89aaf6c840d36e6e9ffef779199b577077b  simulations/results/E5_domain_economy.json
2177fb54f7efdf9f6dc20f89be276e836bfea9f269bc3d6fa9d3d3e1debdfcb5  simulations/results/E6_session_length.json
4c37b7a6d51b03faa7be537941258ee4fd04606ed8a01207541cdc1bda8c9ce7  simulations/results/E7_bursty_burns.json
57982fff16f95a8ff8bd7dd33c6e14528fe64f4dc29cbde22419500dd9364594  simulations/results/E8_budget_allocation.json
282f378f335ef444a1af5682b67ff80716a37d6640cf05cc0fa0f93fe2895bf1  simulations/results/E9_multiprovider.json
054f6a3377cca15ae1cbe8570b78a18c5f4ae113a06b899c5c63550a30bff6c7  simulations/results/E10_discovery_robustness.json
b123bfd252420c59696aeb85bb83517bb341949bc5591a0d477b8c9fc0e98f55  simulations/results/R1_exact_validation.json
aa038e30ef909dc3da99f768617195ab4d5a76d13343faec8587e44b8e4965e8  simulations/results/R2_frontiers.json
a310f1066dc5d5cba25df1a8267548892b922883f3ce45f93b198f5ed8f523c1  simulations/results/R3_budget_split.json
90a5d0b0d012286d518c857c206e8e731058b71dcb8b48412789cdc378b06279  simulations/results/R4_strategic_censor.json
aa707f8ddb6cc360ab5613596340cac0a62ab39f5d4ea6eddb6aeb9e4b7cfa85  simulations/results/R5_diversification.json
25a50cfd4554470e3dab7f62985f3ab379ed7fb918f8226bab5f32416f7f784d  simulations/results/R6_heavy_tail_discovery.json
9fcd55ba704d5a66b2303bf427f0bf056bf966a80366f76cf096d23f6b5a80db  simulations/results/R7_sync_discovery.json
27028e166ff295b13664981e82325b2155f528184b10087bab810fb36fa5b6d0  simulations/results/R8_mint_exposure.json
b3dc2fa3b6c429d43f024493ba9b82709d344f9ddd5312c126a0a73a348befdf  simulations/results/R9_range_blocking.json
ee8f378d282fe6d9a97a1f0211c036fde4050b59e2928f9ae4077ecf2451a756  simulations/results/R10_perunit_normalization.json
1eab783d408ef758ab84c6348058be685695f23aafac4aef2e535dcd3127a41f  simulations/results/R11_profiles.json
3263df14d4aca732263dbf33b68eae0aae03be177cb0bd921f748de40a510bdd  simulations/results/R12_figures.json
2ed397dfdf8c3efa540146f38496d020b0eee3e39fa43ea4040146cbfabe7ecc  simulations/results/R13_rotation_speed.json
b58d5ba5421a3656af5ad53af827a2f19786c039830b9e4934a86be8980b0c38  simulations/code/exact.py
5fafb3340b0204408a24899c00902e3b178c60d71f9051c05bd72b865ec6f304  simulations/code/exact_experiments.py
ecbec4445a888dd50611c6743d6be0108d22cb042ce270bab0d316df1c762526  figures/frontier.pdf
e70893b49affd7c4bfefa1ac073f397456a50f8c46bc29ca51b9dd53cb2d6b6d  figures/phase.pdf
EOF
```

Every line ends in `OK` on the shipped files.

## The paper's numbers from the shipped files

This snippet, run from the repository root, prints the paper's numbers that
the result files store, by section.

```bash
python3 - <<'EOF'
import json

def load(name):
    with open(f"simulations/results/{name}.json") as f:
        return json.load(f)

R1, R2, R4, R5, R6, R7, R8, R10, R13 = map(load, (
    "R1_exact_validation", "R2_frontiers", "R4_strategic_censor", "R5_diversification",
    "R6_heavy_tail_discovery", "R7_sync_discovery", "R8_mint_exposure",
    "R10_perunit_normalization", "R13_rotation_speed"))
fmt = lambda xs, d=3: ", ".join(f"{x:.{d}f}" for x in xs)
row = lambda rows, **kw: next(r for r in rows if all(r[k] == v for k, v in kw.items()))
K, dense, first = R2["dense"]["kmax"], R2["dense"], R2["min_kmax_beta_star_above_1"]
at = lambda curve: [curve[K.index(k)] for k in (2, 4, 8, 16, 32)]

print("Sec. 5.2  beta*_avg at k_max = 2..32:", fmt(at(dense["avg"]["0.95"])),
      "| c_a/alpha:", fmt([R2["c_a"] / 0.95]))
print("Sec. 5.2  beta*(0.95,5) at k_max = 2..32:", fmt(at(dense["interval"]["0.95|5.0"])),
      "| W_5^addr:", fmt([R2["address_window"]["5.0"]]))
print("Sec. 5.2  limit:", fmt([R2["large_kmax_interval_beta_star"]["0.95"]["5.0"]["8192"]]),
      "| first k_max with beta*(0.95,5) > 1:", first["0.95"]["5.0"]["kmax"])
print("Sec. 5.2  first k_max with beta* > 1 grows with T = 1, 2, 5, 10, 20:",
      [first["0.95"][T]["kmax"] for T in ("1.0", "2.0", "5.0", "10.0", "20.0")],
      "| and with the target alpha = 0.9, 0.95, 0.99 (T = 5):",
      [first[a]["5.0"]["kmax"] for a in ("0.9", "0.95", "0.99")])
print("Sec. 5.2  beta*(0.95,T) at k_max = 8, T = 1, 5, 10, 20:",
      fmt(row(R2["table"], alpha=0.95, kmax=8, T=T)["beta_star_interval"]
          for T in (1.0, 5.0, 10.0, 20.0)))
pois = R4["policies"]["8"]["poisson"]
print("Sec. 5.2  k_max = 8, beta = 1: time average", fmt([pois["timeavg_at_beta"]["1.0"]]),
      "| A_5:", fmt([pois["interval_at_beta"]["1.0"]]))
print("Fig. 1  first k_max with beta* > 1 (time average, T = 1, 5, 20):",
      [first["0.95"]["time_average"]] + [first["0.95"][T]["kmax"] for T in ("1.0", "5.0", "20.0")])

ratios = R13["ratios_mu_over_lam_a"]
rot = {la: row(R13["rows"], n=8, kmax=8, lam_a_over_lam_intro=la) for la in (1.0, 10.0, 60.0)}
i1 = min(range(len(ratios)), key=lambda i: abs(ratios[i] - 1.0))
print("Sec. 5.3  mu/lam_a = 1: c_a", fmt([rot[1.0]["c_a"][i1]]),
      "| W^addr at lam_a T = 5:", fmt([rot[1.0]["addr_window_T5"][i1]]))
print("Sec. 5.3  perfect address layer:", fmt([rot[1.0]["beta_star_interval_limit_mu_inf"]]),
      "| thresholds at lam_a T = 5, 50, 300:",
      fmt([rot[la]["saturation_ratio_interval"]["0.01"] for la in (1.0, 10.0, 60.0)], 2),
      "| time average:", fmt([rot[1.0]["saturation_ratio_timeavg"]["0.01"]], 2),
      "| grid step:", fmt([ratios[1] / ratios[0]]))
print("Sec. 5.3  W_5^addr = alpha at lam_a/lam_intro =", fmt([R13["timescale_caveat_canonical"]
      ["lam_a_over_lam_intro_where_window_equals_alpha"]], 1))
none = lambda x: -1.0 if x is None else x          # null: no beta meets the target
drop = lambda xs: max([none(a) - none(b) for a, b in zip(xs, xs[1:])] + [0.0])
by_n = lambda r, key, i: [row(R13["rows"], n=n, kmax=r["kmax"], lam_a_over_lam_intro=r[
    "lam_a_over_lam_intro"])[key][i] for n in (4, 8, 16)]
drops = lambda key: ", ".join(f"{d:.1e}" for d in (
    max(drop(r[key]) for r in R13["rows"]),
    max(drop(by_n(r, key, i)) for r in R13["rows"] if r["n"] == 4 for i in range(len(ratios)))))
print("Thm. 5.3  beta*(0.95,5) nondecreasing in k_max (R2):",
      R2["interval_beta_star_nondecreasing_in_kmax"],
      "| largest drop along mu/lam_a and from n = 4 to 8 to 16 (R13):", drops("beta_star_interval"),
      "| W_5^addr:", drops("addr_window_T5"))

p8, res = R4["policies"]["8"], R4["reserve"]["8"]["strike_all"]
print("Sec. 5.4  strike-all beta*:", fmt([p8["strike_all"]["beta_star_interval"]]),
      "| beta*_avg:", fmt([pois["beta_star_timeavg"], p8["strike_all"]["beta_star_timeavg"]]),
      "| batches of 2, 4:", fmt([p8["batch_j2"]["beta_star_interval"],
                                 p8["batch_j4"]["beta_star_interval"]]),
      "| reserve r = 1, 2, 4:", fmt([res[r]["beta_star_interval"] for r in ("1", "2", "4")]))
mdp = R4["best_response_timeavg_mdp"]["rows"]
print("Sec. 5.4  MDP points:", len(mdp),
      "| strike-all optimal at all:", all(x["optimal_policy_equals_strike_all"] for x in mdp))
inf = R8["table"]["8"]["inf"]
print("Sec. 5.4  exposure at theta = inf, rho = 0.25, 0.5, 0.75, 0.9:",
      fmt(inf[x]["beta_star_interval"] for x in ("0.25", "0.5", "0.75", "0.9")),
      "| rho = 1:", inf["1.0"]["status"])
print("Sec. 5.4  bursts b = 2, 4, 8:",
      fmt(R1["E7"]["per_b"][b]["beta_star_exact_root"] for b in ("2", "4", "8")),
      "| providers P = 1, 2, 4, 8:",
      fmt(R5["by_kmax"]["8"]["P"][P]["pooled"]["beta_star_interval"] for P in ("1", "2", "4", "8")))

sweep, indep = row(R7["rows"], n=8, s=1.0), row(R7["rows"], n=8, s=0.0)
print("Rem. 4.4  all blocked under sweeps:", fmt([sweep["P_c0"]]),
      "| p^n:", f"{indep['p_pow_n']:.1e}",
      "| W_5^addr at s = 0, 0.01:",
      fmt([indep["addr_window_T5"], row(R7["rows"], n=8, s=0.01)["addr_window_T5"]]))
law = {x["law"]: x for x in R6["rows"]}
hyper = law["hyperexp_0.9@0.1_0.1@9.1"]
print("Rem. B.1  p (exponential, deterministic, hyperexponential):",
      fmt([law["exponential"]["p_quadrature"], law["deterministic"]["p_quadrature"],
           hyper["p_quadrature"]], 2), "| c_a:", fmt([hyper["c_a_n8"]]))
e2 = R1["E2"]["stats_interval"]
rest = [v for k, v in R1["summary"].items()
        if "max_abs_diff" in k and k != "E2_interval_max_abs_diff"]
print("App. B  E2 sweep:", e2["n_points"], "points,", R1["E2"]["seeds"], "seeds",
      "| largest difference:", fmt([e2["max_abs_diff"]], 4),
      "| within 3 SE:", f"{100 * e2['frac_within_3se']:.1f}%",
      "| largest difference elsewhere:", fmt([max(rest)], 4))
z = [abs(m[k]) for f in (R4, R5, R7, R8) for m in f["mc_check"] for k in m
     if (k == "z" or k.startswith("z_")) and m[k] is not None]
lim = R8["theta_inf_limit_check"]
print("App. C  largest Monte Carlo |z|:", fmt([max(z)], 2),
      "| theta-limit check at theta = 1e3, 1e4:",
      ", ".join(f"{max(x['max_abs_diff_window'] for x in lim if x['theta'] == t):.1e}"
                for t in (1e3, 1e4)))
pn, cr = R10["results"]["8"]["delta=lam_disc"], R10["results"]["8"]["constant_rate"]
live = 1 - pn["pi0_at_beta_star"]
print("App. C  per-name discovery: target met up to delta =", fmt([pn["delta_at_beta_star"]]),
      "| Pr[K >= 1]:", fmt([live]),
      "| burns per mint interval:", fmt([pn["realized_burn_at_beta_star"]]),
      "| while a name is live:", fmt([pn["realized_burn_at_beta_star"] / live]),
      "| constant-rate beta*:", fmt([cr["beta_star_interval"]]))
EOF
```

Expected output:

```
Sec. 5.2  beta*_avg at k_max = 2..32: 0.257, 0.577, 0.840, 0.980, 1.035 | c_a/alpha: 1.053
Sec. 5.2  beta*(0.95,5) at k_max = 2..32: 0.098, 0.355, 0.661, 0.865, 0.963 | W_5^addr: 0.998
Sec. 5.2  limit: 1.016 | first k_max with beta*(0.95,5) > 1: 63
Sec. 5.2  first k_max with beta* > 1 grows with T = 1, 2, 5, 10, 20: [34, 43, 63, 87, 128] | and with the target alpha = 0.9, 0.95, 0.99 (T = 5): [31, 63, 369]
Sec. 5.2  beta*(0.95,T) at k_max = 8, T = 1, 5, 10, 20: 0.755, 0.661, 0.610, 0.552
Sec. 5.2  k_max = 8, beta = 1: time average 0.889 | A_5: 0.659
Fig. 1  first k_max with beta* > 1 (time average, T = 1, 5, 20): [20, 34, 63, 128]
Sec. 5.3  mu/lam_a = 1: c_a 0.996 | W^addr at lam_a T = 5: 0.872
Sec. 5.3  perfect address layer: 0.665 | thresholds at lam_a T = 5, 50, 300: 2.52, 4.00, 5.66 | time average: 1.12 | grid step: 1.122
Sec. 5.3  W_5^addr = alpha at lam_a/lam_intro = 29.5
Thm. 5.3  beta*(0.95,5) nondecreasing in k_max (R2): True | largest drop along mu/lam_a and from n = 4 to 8 to 16 (R13): 2.5e-12, 0.0e+00 | W_5^addr: 1.1e-12, 0.0e+00
Sec. 5.4  strike-all beta*: 0.064 | beta*_avg: 0.840, 0.313 | batches of 2, 4: 0.671, 0.647 | reserve r = 1, 2, 4: 0.237, 0.367, 0.522
Sec. 5.4  MDP points: 17 | strike-all optimal at all: True
Sec. 5.4  exposure at theta = inf, rho = 0.25, 0.5, 0.75, 0.9: 0.510, 0.352, 0.185, 0.078 | rho = 1: none
Sec. 5.4  bursts b = 2, 4, 8: 0.523, 0.314, 0.066 | providers P = 1, 2, 4, 8: 0.008, 0.092, 0.311, 0.661
Rem. 4.4  all blocked under sweeps: 0.040 | p^n: 1.5e-05 | W_5^addr at s = 0, 0.01: 0.998, 0.949
Rem. B.1  p (exponential, deterministic, hyperexponential): 0.25, 0.05, 0.70 | c_a: 0.945
App. B  E2 sweep: 148 points, 24 seeds | largest difference: 0.0052 | within 3 SE: 99.3% | largest difference elsewhere: 0.0086
App. C  largest Monte Carlo |z|: 2.32 | theta-limit check at theta = 1e3, 1e4: 1.5e-04, 1.5e-05
App. C  per-name discovery: target met up to delta = 0.212 | Pr[K >= 1]: 0.991 | burns per mint interval: 0.943 | while a name is live: 0.952 | constant-rate beta*: 0.661
```

The text of Section 5.2 gives the first k_max with beta* > 1 only for
(0.95, 5), 63, and Figure 1 marks it for the time average and for T = 1, 5
and 20 (20, 34, 63 and 128, the line "Fig. 1"). The paper does not report
the other values of the line "first k_max with beta* > 1 grows with ...",
43, 87, 31 and 369. They show what the text says, that the smallest buffer
grows with the window length and with the target. The thresholds of Section
5.3 are grid values on a grid of mu/lambda_a with step 2^(1/6) = 1.122.
`extra_values.py` prints the exact thresholds, which the grid values exceed
by 1.9% to 6.4%, within the 7% that Section 5.3 states. The largest |z| of
the Monte Carlo checks are 2.26 (R4), 1.72 (R5), 1.10 (R7) and 2.32 (R8),
from 16 seeds each.

The line "Thm. 5.3" checks part (iv) of Theorem 5.3 on the stored frontiers.
R2's flag covers the 120 interval frontiers of its `table` (alpha = 0.9, 0.95
and 0.99, T = 1, 2, 5, 10 and 20, k_max = 2 to 256). In the 18 rows of R13
(n = 4, 8 and 16, k_max = 8 and 32, lambda_a T = 5, 50 and 300),
beta*(0.95,5) falls along the grid of mu/lambda_a by at most 2.5e-12, which
is rounding, and never falls from n = 4 to 8 to 16 at the same k_max,
lambda_a and mu/lambda_a. A null frontier, where no beta meets the target,
counts as below every frontier, and nulls occur only at the slowest rotations
of each row. The address window W_5^addr, through which n and mu enter the
frontier (Appendix A), behaves the same way.

The last line is the per-name discovery of Appendix C, read from
`results["8"]["delta=lam_disc"]` of R10, in which the censor finds each live
name at rate delta: `delta_at_beta_star` (0.21223), `pi0_at_beta_star`
(0.00947) and `realized_burn_at_beta_star` (0.94293, that is delta E[K]). The
rate that step 7 of Section 7 estimates, burns per unit of time with a live
name, is 0.94293 / (1 - 0.00947) = 0.952. By flow balance the burns per mint
interval equal the admitted mints, Pr[K < k_max], so this rate is also
Pr[K < k_max] / Pr[K >= 1], the form of Appendix C, which `extra_values.py`
prints. The constant-rate frontier is
`results["8"]["constant_rate"].beta_star_interval` (0.66134). R10's other two
normalizations, `delta=lam_disc/kmax` and `delta=lam_disc/E_const[K]`,
reparametrize the same family and reach the target at the same delta.

## Values that no result file stores

Two scripts print the rest of the paper's model values.

```bash
python3 exact.py          # self-test of the solver
python3 extra_values.py   # short exact computations
```

`python3 exact.py` prints the accuracy figures of Appendix B (2e-14 and
4.4e-15 in the paper) in its first and fourth lines.

```
spectral vs dense expm (40 random chains): max |diff| = 1.99e-14
LinearCTMC(batch b=1) == birth-death pool: ok
address stationary P[c=0] = p^n: ok
spectral vs Krylov (m = 300..1200): max |diff| = 4.44e-15
strategic('poisson', r=2) == constant pool: ok
providers(P=8,kp=1,pooled) == constant pool: ok
exposure(rho=0) == constant pool: ok
sweep chain P[c=0] = lam_a/(lam_a + n mu): ok
self-test passed
```

`python3 extra_values.py` prints the values of Figure 2's description,
Section 5.3, Section 7, Appendix B and Appendix C that no result file stores.
It also runs the single-crossing grid check of Appendix B ("Numerical
method") for the eight frontiers of Section 5.4 and Appendix C that the result
files store without one, and it recomputes with `exact.py` the per-name
discovery values of Appendix C, part of which R10 stores, with the
flow-balance form of the rate that step 7 estimates. It runs in about three
seconds and writes nothing.

```
Figure 2, interval availability A_5 at beta = 2:
  k_max = 4: 0.027, k_max = 8: 0.050, k_max = 16: 0.052, k_max = 32: 0.052, k_max = 64: 0.052
Section 5.3, address window W_T^addr at n = 8 (lambda_a = 1, so T = lambda_a T):
  mu/lambda_a = 1, lambda_a T = 5: 0.872
  mu/lambda_a = 1, lambda_a T = 15: 0.669
  mu/lambda_a = 1, lambda_a T = 60: 0.204
Section 5.3, mu/lambda_a at which beta* comes within 0.01 of its limit (n = 8, k_max = 8), exact and on the grid of R13:
  interval, lambda_a T = 5: 2.472, grid 2.520 (1.9% above)
  interval, lambda_a T = 50: 3.913, grid 4.000 (2.2% above)
  interval, lambda_a T = 300: 5.408, grid 5.657 (4.6% above)
  time average: 1.055, grid 1.122 (6.4% above)
Section 5.3, smallest mu/lambda_a with W_T^addr >= 0.95 (mean time to block one minute):
  one-hour session (lambda_a T = 60): mu/lambda_a = 2.49, one rotation every 24 s per endpoint
  one-day session (lambda_a T = 1440): mu/lambda_a = 4.63, one rotation every 13 s per endpoint
Section 7, one exact interval frontier at k_max = 8: 7.1 ms (best of 5 x 20 runs; machine-dependent)
Appendix B, closed-form address bound after Corollary B.2 (n = 8, mu = 3, T = 5):
  1 - p^n (1 + n mu T) = 0.99815; exact W_5^addr = 0.99825
Appendix B, single-crossing grid check of the frontiers of Section 5.4 and Appendix C that no result file checks:
  bursts, b = 2: beta* = 0.523, single crossing: True
  bursts, b = 4: beta* = 0.314, single crossing: True
  bursts, b = 8: beta* = 0.066, single crossing: True
  strike-all with reserve, r = 1: beta* = 0.237, single crossing: True
  strike-all with reserve, r = 2: beta* = 0.367, single crossing: True
  strike-all with reserve, r = 4: beta* = 0.522, single crossing: True
  strike-all, time average, k_max = 8: beta*_avg = 0.313, single crossing: True
  strike-all, time average, k_max = 32: beta*_avg = 0.665, single crossing: True
Appendix C, bound (1 - rho) beta* at k_max = 8 (beta*(0.95, 5) = 0.661):
  rho = 0.25: 0.496, rho = 0.5: 0.331, rho = 0.75: 0.165, rho = 0.9: 0.066
Appendix C, per-name discovery at k_max = 8 (the censor burns at rate delta K):
  the target (0.95, 5) holds up to delta = 0.212 per mint interval, where Pr[K >= 1] = 0.991 and the censor burns 0.943 names per mint interval
  there it burns 0.952 names per mint interval while a name is live (the rate that step 7 of Section 7 estimates), against beta* = 0.661 for a constant-rate censor
  by flow balance that rate is Pr[K < k_max] / Pr[K >= 1] = 0.943 / 0.991 = 0.952
  that rate rises with delta up to beta* (grid check: True) and equals beta* = 0.661 at delta = 0.0999, where A_5 = 0.997
```

The timing depends on the machine and its load. Repeated runs on the reference
workstation printed 6.5 to 9.1 ms, and the paper reports about 8 ms. The value
at lambda_a T = 5 repeats `R13_rotation_speed.json`, and the grid values of the
thresholds are its `saturation_ratio_interval["0.01"]` and
`saturation_ratio_timeavg["0.01"]`. The first two per-name discovery lines
equal the R10 values above. The third computes the same rate without counting
burns, as Pr[K < k_max] / Pr[K >= 1], the form of Appendix C, and its
Pr[K < k_max] = 0.943 equals the burns per mint interval of the first line,
as flow balance requires. The last one supports the last sentence of
Appendix C. The rate that step 7 estimates rises with delta, which Lemma A.2
gives for every delta and the grid checks up to beta*, beyond which the rate,
delta E[K | K >= 1], exceeds delta and so beta*. It reaches the constant-rate
beta* = 0.661 at delta = 0.0999, well below 0.212, where A_5 = 0.997. A
deployment that keeps that estimate below beta* thus meets the target
(0.95, 5) against this censor too. The result files store single-crossing
checks for the interval frontiers of `R2_frontiers.json`, of the policy table
of `R4_strategic_censor.json`, of `R5_diversification.json` and of
`R10_perunit_normalization.json`. The two strike-all time-average frontiers
are `policies["8"].strike_all.beta_star_timeavg` and
`policies["32"].strike_all.beta_star_timeavg` of `R4_strategic_censor.json`,
and both are also MDP points of Appendix C (`is_strike_all_root`). The
frontiers at theta = infinity in `R8_mint_exposure.json` are those of a
birth–death pool, which needs no such check.

## Figures

| file | written by (repository root) | paper item | SHA-256 |
|---|---|---|---|
| `figures/frontier.pdf` | `python3 paper/figures/make_figures.py` | Figure 1 | `ecbec4445a888dd50611c6743d6be0108d22cb042ce270bab0d316df1c762526` |
| `figures/phase.pdf` | `python3 paper/figures/make_figures.py` | Figure 2 | `e70893b49affd7c4bfefa1ac073f397456a50f8c46bc29ca51b9dd53cb2d6b6d` |

The script reads `E2_phase_transition.json`, `R1_exact_validation.json` and
`R2_frontiers.json` and prints 85 checks of the plotted values. To keep the
shipped PDFs, write to another directory and compare.

```bash
python3 paper/figures/make_figures.py --outdir figures_check
cmp figures/frontier.pdf figures_check/frontier.pdf
cmp figures/phase.pdf figures_check/phase.pdf
```

With Python 3.13.7, NumPy 2.2.4, SciPy 1.15.3, Matplotlib 3.10.1 (Ubuntu
package 3.10.1+dfsg1 with fontTools 4.55.3) and pandas 3.0.6, the script ends
with "all checks passed" and `cmp` prints nothing, because the PDFs are
identical byte for byte. Other Matplotlib or fontTools builds can embed
different bytes while all 85 checks pass.

Two outputs of the code are not included, because the paper does not use
them. `python3 paper/figures/make_figures.py --all` also writes
`figures/robust.pdf`, which plots the frontiers of Section 5.4 and runs 173
checks, and the FIG step of `exact_experiments.py` writes four figures to
`../figures_exact/`.

## Rerun and compare

The scripts overwrite the files in this directory, so rerun them in a copy.
From the repository root:

```bash
mkdir ../rerun && cp -r simulations ../rerun/
(cd ../rerun/simulations/code && python3 run_experiments.py && python3 exact_experiments.py)
```

To rerun only the exact suite on the shipped E files, leave out
`python3 run_experiments.py &&`. Then compare the copy with the shipped files,
again from the repository root. The comparison ignores `_meta.runtime_s` and
`_meta.generated_utc`, and it counts R1's `inputs`, the SHA-256 and size of
each E file read, separately.

```bash
python3 - <<'EOF'
import json, os

ref, new = "simulations/results", "../rerun/simulations/results"

def leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if not (path == "/_meta" and k in ("runtime_s", "generated_utc")):
                yield from leaves(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, o

num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
for name in sorted((f for f in os.listdir(new) if f.endswith(".json")),
                   key=lambda f: (f[0], int(f.split("_")[0][1:]))):
    a = dict(leaves(json.load(open(f"{ref}/{name}"))))
    b = dict(leaves(json.load(open(f"{new}/{name}"))))
    keys = [k for k in a.keys() | b.keys() if not k.startswith("/inputs/")]
    diffs = [abs(a[k] - b[k]) for k in keys if num(a.get(k)) and num(b.get(k))]
    other = sum(1 for k in keys if not (num(a.get(k)) and num(b.get(k))) and a.get(k) != b.get(k))
    inputs = sum(1 for k in a.keys() | b.keys() if k.startswith("/inputs/") and a.get(k) != b.get(k))
    print(f"{name}: {len(diffs)} numbers, max |diff| {max(diffs, default=0):.2g}, "
          f"other differences {other}" + (f", R1 input hashes differing {inputs}" if inputs else ""))
EOF
```

What the reference reruns gave on the reference workstation, with the
versions above:

- Two reruns of E1 to E10 took 57 and 58 minutes on one core and reproduced
  every number exactly (max |diff| 0 in all ten files).
- Reruns of the exact suite took about five minutes each and reproduced every
  number of the 13 R files exactly, except up to five window probabilities in
  `R9_range_blocking.json`, which the paper does not report. These differ in
  their last digits, by at most 2.2e-14, within the 3 x 10^-14 that
  Appendix E reports, and they change from rerun to rerun. They are the
  residue of a random norm estimate in SciPy's `expm_multiply`, which draws
  random vectors from NumPy's global random generator, and
  `exact_experiments.py` does not seed that generator. The affected chains,
  16 endpoints over 4 providers, have 625 states, 624 of them up, and the
  solver uses a dense matrix exponential only up to 400 up-states
  (`ctmc_window`). Two runs of R9 with the generator seeded by
  `numpy.random.seed(0)` gave identical numbers, which still differed from the
  shipped file in two such values.
- On the shipped E files, R1's `inputs` match. After the full rerun, the
  comparison reported "R1 input hashes differing 9", because R1 records the
  SHA-256 and size of the E files it read and nine rerun E files differ from
  the shipped ones in `_meta.runtime_s`. This is expected, and it is why the
  shipped E files must not be replaced by a rerun.

Other versions of Python, NumPy or SciPy can change the last digits of the
results, and so can other builds of the same versions. The reference runs used
Ubuntu's NumPy and SciPy packages with the reference BLAS and LAPACK, while
the PyPI wheels bundle OpenBLAS (see `README.md` in the repository root). The
Monte Carlo columns of `R6_heavy_tail_discovery.json` use SciPy's samplers and
can change with SciPy, while the paper's values in that file come from its
quadrature columns. `exact_experiments.py` saves the figures of
`../figures_exact/` with Matplotlib's default PDF metadata, which includes the
local creation time.
