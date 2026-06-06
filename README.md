# Reproducibility package

Public code for **"Block-A-Mole: The Sustainability Frontier of Moving-Target
Censorship Resistance."**

One script regenerates **every figure and results table in the paper**, with
output files numbered exactly as they appear in the paper.

```
python3 reproduce.py
```

This runs the full rotation-game simulation suite locally (no cloud access or
privileged deployment) and writes, into `output/`:

| artifact            | paper item                                            |
|---------------------|-------------------------------------------------------|
| `figure_1.pdf`      | Fig. 1 — address blocking is a losing strategy        |
| `figure_2.pdf`      | Fig. 2 — the sustainability frontier (phase transition) |
| `figure_3.pdf`      | Fig. 3 — rotation speed is not the lever              |
| `figure_4.pdf`      | Fig. 4 — session length: (a) curves, (b) frontier     |
| `figure_5.pdf`      | Fig. 5 — robustness: (a) bursty (b) diversification (c) discovery (d) law |
| `figure_6.pdf`      | Fig. 6 — closed-form frontier β\*(n, kₘₐₓ) per censor |
| `figure_7.pdf`      | Fig. 7 — the censor's optimal budget split            |
| `figure_8.pdf`      | Fig. 8 — the domain-economy operating recipe          |
| `table_1.txt`       | Table 1 — adversary profiles                          |
| `table_2.txt`       | Table 2 — closed-form law vs. simulation              |
| `table_3.txt`       | Table 3 — interval frontier (renewal vs. simulation)  |
| `table_4.txt`       | Table 4 — simulator transition rates                  |
| `output/data/*.json`| raw per-experiment data behind each figure            |

Figures are vector PDF; tables are plain text. Multi-panel paper figures (4 and
5) are emitted as a single composite PDF with the lettered panels, matching the
paper layout.

## Usage

```bash
python3 reproduce.py            # full sweeps, paper settings (~10-15 min)
python3 reproduce.py --quick    # smaller sweeps / shorter horizons (a fast pass)
python3 reproduce.py --outdir DIR
python3 reproduce.py --no-data  # skip writing the raw JSON
```

`--quick` reproduces every figure and table but with fewer seeds and shorter
simulated horizons, so curves are noisier and the empirical frontiers shift by
about the sweep resolution. Use the default (full) settings for paper-quality
output.

## What the model is

The censor–defender game decomposes into two independent birth–death layers.

* **Address layer** — `num_clear`, the number of endpoints with an unblocked IP
  (`clear → blocked` at rate `λ_a·num_clear`, recovery via rotation at rate
  `μ·(n − num_clear)`).
* **Domain layer** — `K`, the number of live unblocked registrable domains, a
  capped birth–death chain (mint at `λ_intro`, burn at `λ_disc`, buffer `kₘₐₓ`).

The system is reachable iff `num_clear ≥ 1` **and** `K ≥ 1`. The dimensionless
control is the **domain burn rate** `β = λ_disc / λ_intro`. Unless noted, the
canonical configuration is `n = 8` endpoints, `μ/λ_a = 3`, buffer `kₘₐₓ = 8`,
target `α = 0.95`.

## Files

```
reproduce.py        master script: runs experiments E1–E10, then renders every
                    numbered figure (PDF) and table (TXT)
theory.py           closed-form predictions (geometric IP bound, π₀, A, β*)
rotation_game.py    the event-driven (Gillespie) simulator
censor_models.py    calibrated adversary presets (GFW, TSPU, Iran)
requirements.txt    numpy, scipy, matplotlib
```

The figure ↔ experiment mapping (experiment keys `E1`–`E10`) is documented in
`reproduce.py`.

## Requirements

Python ≥ 3.9 with `numpy`, `scipy`, `matplotlib`:

```bash
pip install -r requirements.txt
```

## Validation, not calibration

This is model-level validation: the closed-form analysis and an independent
simulation agree (Tables 2–3), and the qualitative predictions survive stresses
the closed form omits — state-dependent discovery, bursty and provider-correlated
burns (Fig. 5). Adversary *mechanisms* are fixed to documented GFW, TSPU, and
Iranian designs; the dimensionless presets are deliberately adversary-favorable,
so the reported guarantees are conservative. Fitting free rates to a specific
censor is a deployment step (against public OONI / Censored Planet archives) and
is intentionally out of scope here.

## License

MIT (code) / CC BY 4.0 (generated data). Released for open reuse as a shared,
theory-grounded testbed for the censorship-resistance community.
