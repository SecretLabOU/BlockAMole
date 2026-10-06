# Simulator and exact solver

This directory holds the event-driven simulator and the exact solver for the
two-layer moving-target model of *Block-A-Mole: The Sustainability Frontier of
Moving-Target Censorship Resistance* (Appendix E of the paper). Both run
locally. They need no network access, cloud account or third-party data.

The simulator samples the Markov model by the next-event method, and the exact
solver (`exact.py`) computes the same quantities without Monte Carlo error.
Their agreement (R1) checks the implementations, not the model, because both
assume independent address and name layers. The generic birth–death routine
of the simulator (`rotation_game._simulate_birth_death`) takes the birth and
death rates as functions of the state, plus a jump size for burns, so it
serves as a testbed for variants of the model beyond the closed forms.

## Layout

```
code/
  theory.py              closed forms (address layer p^n, pi_0, A, time-average beta*)
  rotation_game.py       event-driven (Gillespie) simulator of both layers
  censor_models.py       illustrative presets (GFW-, TSPU- and Iran-like), not
                         fitted to any censor
  run_experiments.py     simulation experiments E1–E10, writes ../results/E*.json
  exact.py               exact CTMC solver: stationary laws, interval
                         availability pi_U expm(Q_UU T) 1, frontiers, self-test
  exact_experiments.py   exact experiments R1–R13 and FIG, writes ../results/R*.json
  extra_values.py        prints the paper's values that no result file stores
  figstyle.py            shared Matplotlib style, reads paper.mplstyle
  paper.mplstyle
results/                 the 23 result files behind the paper (see results/README.md)
requirements.txt
```

`paper/figures/make_figures.py` in the repository root draws the paper's
Figures 1 and 2 from these result files. `run_experiments.py` and
`exact_experiments.py` create `../results/` when they start, and
`exact_experiments.py` also creates `../figures_exact/`, where its FIG step
writes four auxiliary figures that the paper does not use.

## Model in one paragraph

The model has two birth–death layers whose clocks are independent by
assumption. The **address layer** tracks `num_clear`, the number of endpoints
with an unblocked IP (`clear→blocked` at rate `lam_a·num_clear`, recovery via
rotation at rate `mu·(n−num_clear)`). The **name layer** (the domain layer in
the code) tracks `K`, the number of live unblocked names, a capped birth–death
chain (mint at `lam_intro`, burn at `lam_disc`). A name is the unit the censor
blocks in one action, such as a registrable domain or a platform tenant's
hostname. The system is reachable iff `num_clear ≥ 1` and `K ≥ 1`. The burn
ratio is `beta = lam_disc/lam_intro` (the paper's lambda_burn/lambda_intro),
and the frontier beta*(alpha, T) is the largest beta at which interval
availability over windows of length T still reaches alpha.

## Requirements

Python 3 with NumPy, SciPy, Matplotlib and pandas.
`python3 -m pip install -r simulations/requirements.txt`, run from the
repository root, installs the versions of the reference runs as PyPI builds.
The reference runs used Python 3.13.7 on Ubuntu 25.10, with Ubuntu's packages
of NumPy 2.2.4 and SciPy 1.15.3, which use the reference BLAS and LAPACK
3.12.1, and of Matplotlib 3.10.1 (3.10.1+dfsg1) with fontTools 4.55.3, and
with pandas 3.0.6 from PyPI. The PyPI wheels of NumPy and SciPy bundle
OpenBLAS and can change the last digits of the exact results, and other
Matplotlib builds can change the bytes of the figures.

- `exact_experiments.py` runs its Monte Carlo cross-checks in parallel with
  Python's `fork` start method, one process per core, which Windows lacks.
- `paper/figures/make_figures.py` imports pandas and prints its version.
- If `mutool` (MuPDF) is installed, `make_figures.py` also checks the page
  size, the smallest font size and the page bounds of each PDF. Without it,
  these checks are skipped and the exit status is unaffected.

## Reproduce the paper

The commands run in `simulations/code`.

```bash
python3 exact.py              # self-test of the solver, about 1 s
python3 extra_values.py       # paper values that no result file stores, about 3 s
python3 run_experiments.py    # E1–E10, about one hour on one core
python3 exact_experiments.py  # R1–R13 and FIG, about five minutes on 20 cores
```

`python3 exact.py` prints the accuracy figures of Appendix B (1.99e-14 and
4.44e-15). `run_experiments.py` and `exact_experiments.py` overwrite the
result files in `../results/`. To compare a rerun with the shipped files, run
them in a copy of `simulations/` as `results/README.md` describes.

- `python3 run_experiments.py --only E2,E7` runs a subset of the simulations.
  `--quick` uses 12 seeds and shorter runs, for a fast test only. Its values
  differ from the paper's.
- The ten simulation experiments take about one hour on one core. Their
  `_meta.runtime_s` values sum to 3,356 s.
- The exact suite took 302 s of wall time on a 20-core workstation, as
  Appendix E reports. The `_meta.runtime_s` values of the 13 R files sum to
  300.7 s.
- `exact_experiments.py` starts with R1, which reads all ten E files and
  records the SHA-256 and size of each. Without them it stops at R1. The other
  experiments run alone, for example
  `python3 exact_experiments.py --only R2,R4`.

The paper's two figures are drawn from the repository root.

```bash
python3 paper/figures/make_figures.py --outdir figures_check
cmp figures/frontier.pdf figures_check/frontier.pdf
cmp figures/phase.pdf figures_check/phase.pdf
```

The script reads `E2_phase_transition.json`, `R1_exact_validation.json` and
`R2_frontiers.json`, recomputes the exact curves with `exact.py` and prints a
table of 85 checks of the plotted values against the stored results and the
paper's numbers. It exits with status 1 if a check fails. `cmp` prints nothing
when the files are identical byte for byte, as they are with the versions
above. Other Matplotlib or fontTools builds can embed different bytes while
all checks pass. Without `--outdir` the script overwrites `figures/`. With
`--all` it also draws `robust.pdf`, which plots the frontiers of Section 5.4
of the paper but is not one of its figures, and runs 173 checks.

## Experiments

| key | file | what it computes |
|-----|------|------------------|
| E1 | `E1_ip_geometric.json` | P[all n addresses blocked] vs n, simulation vs p^n (address-layer lemma) |
| E2 | `E2_phase_transition.json` | interval and time-average availability vs beta (the markers of Figure 2) |
| E3 | `E3_mu_heatmap.json` | availability over beta x mu/lam_a, both metrics (exact thresholds: R13) |
| E4 | `E4_beta_star_grid.json` | closed-form time-average beta*(n, kmax) at the illustrative presets |
| E5 | `E5_domain_economy.json` | required mint rate vs burn rate at the simulated frontier (operating recipe) |
| E6–E10 | `E6_…`–`E10_…json` | session length, bursts, the censor's budget split (not reported in the paper), providers with idle per-provider clocks (the paper uses the pooled model of R5), discovery model |

E4 is closed-form. Each simulated point of E1, E2 and E5–E10 averages 24
seeds. E3 averages `max(8, seeds // 2)` = 12 seeds per point, although its
`_meta.seeds` records the run setting, 24. Runs last 1.2e4 to 4e4 mint
intervals, and the first 10% of each run is discarded as warm-up.

Some file and function names (`E2_phase_transition`, `R1_exact_validation`,
`rotation_game`) do not follow the paper's wording. The tables say what each
one computes.

The comments of `exact.py` and `exact_experiments.py` also use labels of their
own for the paper's results, and they stay as they are, because the R files
lock both files by their SHA-256. In `exact.py`, the label in the docstring of
`addr_timeavg` is Lemma 4.3, that of `name_rates_constant` Proposition 4.5,
that of `timeavg_availability` Theorem 5.1, that of `beta_star_avg` Theorem
5.3, and that of the heading "6. Discovery-delay Laplace transform" Remark
B.1. The per-unit pool of `name_rates_perunit`, in which the censor finds
each live name at rate delta, is the per-name discovery of Appendix C, and R10
holds its values.
The figures that the docstring of `exact_experiments.py` lists for the FIG step
are the four auxiliary figures in `figures_exact/`, which the paper does not
use. R10's reference values `pi0_at_beta`, at beta = 0.8, 1.0 and 1.6, are
not reported in the paper. Only the constant-rate value at beta = 1, 1/9,
underlies a paper number, the time average 0.889 = c_a (1 - 1/9) of Section
5.2, which `PAPER_MAP.md` takes from R4.
The heading comment of `r13_rotation` in `exact_experiments.py` says that R13
supports the claim that faster rotation stops moving the frontier once
mu/lam_a is moderate. The paper claims less. Beyond the thresholds of
Section 5.3, faster rotation moves the frontier by less than 0.01, which is
what R13's `saturation_ratio_interval["0.01"]` and
`saturation_ratio_timeavg["0.01"]` measure, and Section 9 says that faster
rotation then barely moves the frontier. In R13's row for n = 8, k_max = 8
and lam_a T = 5, beta*(0.95,5) still rises from 0.656 at mu/lam_a = 2.52 to
its limit of 0.665.

## Exact CTMC engine (`exact.py`) and experiments R1–R13

The simulator samples a Markov model, so every quantity it estimates can be
computed exactly. `exact.py` does this, and `exact_experiments.py` uses it.

* **Time-average availability** = stationary P[up].
* **(alpha,T)-interval availability** = P[up throughout a window of length T]
  for a stationary chain = `pi_U expm(Q_UU T) 1` (U = up states, Q_UU the
  generator with transitions into the down set removed). This is the quantity
  `rotation_game.interval_up_probability` estimates.
* The address and name layers have independent clocks in the model, so system
  availability (both metrics) is the product of the two layers' values.
* **Frontiers** beta* are roots in beta (Brent, xtol 1e-10) of
  availability = alpha, not grid floors. For the birth–death name pools
  availability is nonincreasing in beta (a coupling argument), so the root is
  the frontier. A grid check for a single crossing
  (`exact.check_single_crossing`) is recorded only for the interval roots of
  R2, of R4's policy table, of R5 and of R10. `extra_values.py` runs it for
  the other frontiers that the paper reports from non-birth–death chains, the
  burst roots of R1, the strike-all roots with a reserve of R4 and the
  strike-all time-average roots of R4 at k_max = 8 and 32.
* **Engines.** Birth–death chains use the symmetrized spectral form
  `pi_U expm(Q_UU T) 1 = sum_m (v_m' sqrt(pi_U))^2 exp(lambda_m T)` (all terms
  non-negative, stationary law by detailed balance in log space). Above 200
  states they use SciPy's `expm_multiply` on the symmetrized matrix. That
  routine is Al-Mohy and Higham's scaled truncated Taylor method, although the
  code's comments and self-test output call it "Krylov". The chains for
  bursts, the strategic censor, providers and mint-time exposure are built by
  breadth-first search from an initial state as sparse generators linear in
  the named rates (`LinearCTMC`). The sweep chain (`addr_sweep_generator`) is
  assembled directly as a dense generator. The address layer split over
  providers (`addr_window_providers`) is the Kronecker sum of the
  per-provider chains. All of these use a direct stationary solve, `expm` up
  to 400 up-states and `expm_multiply` above. `python3 exact.py` runs a
  self-test: spectral vs dense expm on 40 random birth–death chains (max
  difference 2e-14), spectral vs `expm_multiply` on constant-rate pools with
  buffers of 300 to 1,200 (4.4e-15, printed as "spectral vs Krylov"), and the
  reductions listed below.

### State spaces (time unit 1/lam_intro, lam_intro = 1)

| chain (experiment) | state | transitions | up set | size |
|---|---|---|---|---|
| address layer (all) | `c` = clear endpoints, 0..n | c→c+1 at `mu(n−c)`; c→c−1 at `lam_a c` | c ≥ 1 | n+1 |
| address, sweeps (R7) | `c` | c→c+1 at `mu(n−c)`; c→c−1 at `(1−s) lam_a c`; c→0 at `s lam_a` | c ≥ 1 | n+1 |
| address, range-blocked (R9) | `c` per provider; jointly `(c_1..c_P)` | per provider: discovery `lam_a + mu g`, recovery `mu(1−g)` per endpoint (Kronecker sum across providers) | Σc ≥ 1 | ∏(n_i+1) |
| name pool, constant (R1–R3) | `K` = live units, 0..kmax | K→K+1 at `lam_intro` (K<kmax); K→K−1 at `lam_disc` | K ≥ 1 | kmax+1 |
| name pool, per-unit (R10) | `K` | K→K+1 at `lam_intro` (K<kmax); K→K−1 at `delta K` | K ≥ 1 | kmax+1 |
| name pool, bursts (R1/E7) | `K` | K→max(0,K−b) at `lam_disc/b` | K ≥ 1 | kmax+1 |
| strategic censor + reserve (R4) | `(A,R,D)`: active (served, discoverable) units, reserve units (undiscoverable), discovered-but-unblocked active units; D ≤ A, A+R ≤ kmax, R ≤ r | mint at `lam_intro` (to active if A=0, else to reserve if R<r, else to active); discovery at `lam_disc` while A−D ≥ 1, then the policy may strike (block all D); if A becomes 0 the reserve activates | A ≥ 1 | 9–560 |
| censor best response (R4) | `(A,D)` with r = 0 | average-reward MDP: after each event the censor blocks any b ≤ D; maximizes P[A=0]; relative value iteration | n/a | 45 / 561 |
| providers (R5) | occupancy counts `(n_0..n_kp)`, n_l = providers holding l units, Σ n_l = P | *pooled*: mint at `lam_intro` into a uniformly random non-full provider, takedown at `lam_disc` empties a uniformly random non-empty provider; *idle*, the idle-clock model (E9): per-provider clocks `lam_intro/P`, `lam_disc/P` | n_0 < P | 9–70 |
| mint-time exposure (R8) | `(E,U)`: exposed / unexposed live units, E+U ≤ kmax | mint at `lam_intro` (exposed w.p. rho); pre-emptive burn at `theta E`; usage burn at `lam_disc` hits a uniformly random live unit | E+U ≥ 1 | 45 / 561 |

Exact reductions checked in code: strategic `poisson` (any r) = constant pool,
providers `pooled` with kp = 1 = constant pool, exposure with rho = 0 =
constant pool, and exposure with theta → ∞ → constant pool with intro rate
`(1−rho) lam_intro`. The last has a largest window difference of 1.5e-4 at
theta = 1e3 and 1.5e-5 at theta = 1e4 over the nine points tested (kmax = 8,
T = 5, rho in {0.25, 0.5, 0.9}, beta in {0.1, 0.3, 0.6}), which is not a bound
over all beta. For the sweep chain, P[c=0] = `lam_a/(lam_a + n mu)` at s = 1.
The chains of R4, R5, R7 and R8 are also checked against independent
unit-level Monte Carlo with 16 seeds each, and all |z| < 2.4 (the largest are
2.26, 1.72, 1.10 and 2.32).

| key | file | content |
|---|---|---|
| R1 | `R1_exact_validation.json` | exact vs the event-driven simulations E1–E10 (implementation check) |
| R2 | `R2_frontiers.json` | beta*_avg and exact interval beta*(alpha,T) vs kmax |
| R3 | `R3_budget_split.json` | censor budget split, corners, corner criterion (not reported in the paper) |
| R4 | `R4_strategic_censor.json` | strategic timing censor, reserve, MDP best response |
| R5 | `R5_diversification.json` | pooled diversification vs single pool vs idle-clock model (E9) |
| R6 | `R6_heavy_tail_discovery.json` | p = E[exp(−mu D)] for mean-1 discovery laws |
| R7 | `R7_sync_discovery.json` | synchronized (sweep) address discovery |
| R8 | `R8_mint_exposure.json` | mint-time exposure (pre-emptive burns) |
| R9 | `R9_range_blocking.json` | range-blocked provider space (crisis regime) |
| R10 | `R10_perunit_normalization.json` | per-unit (per-name) discovery, three normalizations, against the constant-rate pool (Appendix C) |
| R11 | `R11_profiles.json` | exact beta* at the illustrative presets of `censor_models.py` (not fits) |
| R13 | `R13_rotation_speed.json` | beta* vs mu/lam_a under both metrics (rotation-speed saturation) |
| FIG | `R12_figures.json` | lists the auxiliary figures that FIG writes to `figures_exact/`, which the paper does not use |

Convenience entry points for plugging in measured rates:
`exact.frontier_interval(alpha, T, n, lam_a, mu, kmax)`,
`exact.frontier_timeavg(alpha, n, lam_a, mu, kmax)`, and for range blocking
`exact.p_range`, `exact.address_factor_providers`,
`exact.address_factor_regime`, `exact.addr_window_providers`.

`results/README.md` describes each result file and how to compare a rerun
with it. `PAPER_MAP.md` in the repository root maps each number of the paper
to a result file, a printed value or a script.

## License

The code is under the MIT license and the result files under CC BY 4.0 (see
`LICENSE` in the repository root).
