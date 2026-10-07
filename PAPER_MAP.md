# Paper map

This file maps each number and factual statement of the paper that the code
or the data support to the file that holds it, the key or column, and a
command that prints it. It follows the paper section by section. Statements
that the paper takes from cited work are listed where the repository records
the cited value or quote. Others rest on the citation alone.

## How to read the tables

- Paths are relative to the repository root. `E1_ip_geometric.json` to
  `E10_discovery_robustness.json` and `R1_exact_validation.json` to
  `R13_rotation_speed.json` are the result files in `simulations/results/`.
  `run_experiments.py` writes the E files and `exact_experiments.py` the R
  files, both run in `simulations/code`. Every file in
  `data/<analysis>/derived/` is written by `python3 analysis.py`, run in
  `data/<analysis>/` after the downloads that `data/<analysis>/raw/README.md`
  describes.
- JSON keys are written as paths. `dense.interval["0.95|5.0"] @ k_max = 8` is
  the entry of that list at the position of 8 in `dense.kmax`. A row such as
  `rows (n = 8, s = 1.0)` is the list element with those fields. In R13,
  `@ mu/lam_a = 1` means the position of 1 in `ratios_mu_over_lam_a`. Every R
  file records the canonical configuration of Section 5 (n = 8,
  lambda_a = lambda_intro = 1, mu = 3, k_max = 8, T = 5, alpha = 0.95) in
  `_meta.canonical`.
- Row ids such as `G46` are values of the `row_id` column of
  `data/literature/derived/params_table.csv`. Each such row holds the source's
  value, a verbatim quote, its location and the citation. Fact ids such as
  `le_free` are values of the `fact_id` column of
  `data/minting/derived/doc_facts.csv`, which holds each quote with its source
  URL, retrieval time and SHA-256.
- The code names the paper's burn rate lambda_burn `lam_disc` or
  `lambda_disc`.
- Files marked "not shipped" are written by `python3 analysis.py` after the
  downloads, and their `derived/README.md` says why they are left out.

The last column names the command that prints the value. `file` means that
no command prints it, so read it from the file at the key given. Each command
reads only shipped files, runs offline and takes a few seconds, except
SNOW-TSV, which needs the downloaded Snowflake inputs.

- SIM is the snippet under "The paper's numbers from the shipped files" in
  `simulations/results/README.md`, run from the repository root.
- EXACT is `python3 exact.py`, the solver's self-test, run in
  `simulations/code`.
- EXTRA is `python3 extra_values.py`, run in `simulations/code`.
- FIG is `python3 paper/figures/make_figures.py --outdir figures_check`, run
  from the repository root. It redraws Figures 1 and 2 and prints 85 checks.
- BURN is the snippet under "Values in the paper" in
  `data/burn_units/derived/README.md`, run in `data/burn_units`.
- SNOW is the snippet under "The paper's numbers" in
  `data/snowflake/derived/README.md`, run in `data/snowflake`.
- LIT is the snippet under "Statements in the paper and the rows behind them"
  in `data/literature/derived/README.md`. It starts with `cd data/literature`,
  so run it from the repository root.
- MINT is the snippet under "Print the paper's values" in
  `data/minting/derived/README.md`, run in `data/minting`.
- SNOW-SUMMARY, SNOW-MANIFEST and SNOW-TSV run in `data/snowflake`.
  SNOW-TSV needs the rdsys-admin export that `fetch_raw.py` downloads.
  SNOW-MANIFEST and LIT-MANIFEST read `manifest.paper.json`, the copy of the
  shipped manifest that step 1 of the data pipelines makes, when it exists,
  and `raw/manifest.json` otherwise, because a download rewrites the entries
  of `raw/manifest.json`.

  ```
  # SNOW-SUMMARY
  python3 -c "import json; S = json.load(open('derived/summary.json')); print(S['ioda']); print(S['rdsys']['methods_at_last_commit'])"
  # SNOW-MANIFEST
  python3 -c "import json, os; f = 'manifest.paper.json' if os.path.exists('manifest.paper.json') else 'raw/manifest.json'; m = json.load(open(f)); t = sorted(r['retrieved_utc'] for r in m); print(len(m), 'files,', sum(r['size_bytes'] for r in m), 'bytes,', t[0], 'to', t[-1], '| fields', sorted(m[0]))"
  # SNOW-TSV
  python3 -c "import pandas as pd; t = pd.read_csv('raw/gitlab/rdsys-admin/circumvention_log.tsv', sep='\t', dtype=str); r = t[t.commit.str.startswith('4d979dbb1e')].iloc[0]; print('author', pd.Timestamp(r.author_date).tz_convert('UTC'), '| commit', pd.Timestamp(r.commit_date).tz_convert('UTC'), '| versions', t.exported_as.notna().sum())"
  ```

- LIT-MANIFEST runs in `data/literature`.

  ```
  python3 -c "import json, os; f = 'manifest.paper.json' if os.path.exists('manifest.paper.json') else 'raw/manifest.json'; m = json.load(open(f))['files']; t = sorted(v['retrieved_utc'] for v in m.values()); print(len(m), t[0], t[-1])"
  ```

## Abstract

| Statement | File | Key, column or row | Command |
|---|---|---|---|
| "For an illustrative deployment with eight endpoints and a buffer of eight names, beta* is 0.66 for keeping sessions five mint intervals long connected throughout with probability 0.95" | `R2_frontiers.json` | `dense.interval["0.95\|5.0"] @ k_max = 8` (0.6613), at the canonical configuration in `_meta.canonical` | SIM |
| "We compute the required speed, beyond which faster rotation adds little" | `R13_rotation_speed.json` | see Section 5.3 | SIM |
| "Public data show which platform names China and Iran block and Russia orders blocked" | `data/burn_units/derived/burn_units.csv` | `granularity` of the 57 rows (Table 1, see Section 6.1) | BURN |
| "and that even Snowflake depends on names for rendezvous" | `data/snowflake/derived/` | see Section 6.2 | SNOW |
| "Our exact solver, simulator and data pipelines are openly available" | `simulations/code/`, `data/burn_units/`, `data/snowflake/`, `data/literature/`, `data/minting/` | `exact.py`, `exact_experiments.py`, `rotation_game.py` and `run_experiments.py`. The fetch scripts, `analysis.py`, `raw/manifest.json` and `derived/` of each analysis | |

## 1 Introduction

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| "Static circumvention endpoints" | the GFW "blocked new Tor Browser bridges 2 to 36 days after release" | `data/literature/derived/params_table.csv`, `data/literature/derived/derived_values.csv` | rows G46 (2-36 days) and G27 (7, 2, 18, 11 and 36 days after release). Row `gfw_release_to_block_min_max_2016` of `derived_values.csv` (`2-36`) | LIT, file |
| "Many deployments also depend on names" | "Russia and then China extended this to QUIC" | `data/literature/derived/params_table.csv` | rows T10 (between May 2022 and July 2023) and G32 (since 7 April 2024) | LIT |
| "Many deployments also depend on names" | a deployment is "name-dependent if a client cannot reach an endpoint without presenting a name the censor can observe and block persistently" | `simulations/code/exact.py` | a definition. The model counts such a deployment as up only while some name is live and some endpoint is unblocked, so `interval_availability` multiplies `name_window_constant` (K >= 1) by `addr_window` (c >= 1) | |
| "Many deployments also depend on names" | "such as a CensorLess function's hostname or a front domain for the rendezvous of Snowflake" | `data/snowflake/derived/summary.json`, `data/snowflake/derived/churn_published.csv` | for Snowflake, `rdsys.methods_at_last_commit`, whose `http_fronted` is the fronted rendezvous, and the design quote `rendezvous_front_collateral` on blocking the front domain (PDF page 5), see Section 6.2. The CensorLess example rests on its citation | SNOW-SUMMARY, file |
| "Proxy distribution when some users are censor agents" | "simulations find that the rate of new proxies is key to availability" | `data/literature/derived/params_table.csv` | rows N04 (Nasr et al., "Lesson Five") and F01 (Fares et al.) | LIT |
| "The largest burn ratio" | "In an illustrative configuration with eight endpoints, each discovered on average once per mint interval and rotated three times as often" | every R file | `_meta.canonical`: `n` 8, `lam_a` = `lam_intro` = 1 and `mu` 3 | file |
| "The largest burn ratio" | "beta*(0.95,5) is 0.66 for a buffer of k_max = 8 names" | `R2_frontiers.json` | `dense.interval["0.95\|5.0"] @ k_max = 8` (0.6613) | SIM |
| "The largest burn ratio" | "and exceeds 1 only for k_max >= 63" | `R2_frontiers.json` | `min_kmax_beta_star_above_1["0.95"]["5.0"].kmax` (63, `monotone_check` true) | SIM |
| "The largest burn ratio" | a strike-all censor "lowers beta*(0.95,5) about tenfold, to 0.064" | `R4_strategic_censor.json` | `policies["8"].strike_all.beta_star_interval` (0.0641) against `policies["8"].poisson.beta_star_interval` (0.6613), a factor of 10.3 | SIM |
| "The largest burn ratio" | "a small reserve of unexposed names recovers part of the loss" | `R4_strategic_censor.json` | `reserve["8"].strike_all["1"/"2"/"4"].beta_star_interval` (see Section 5.4) | SIM |
| "The largest burn ratio" | "Names are cheap to mint" | `data/minting/derived/porkbun_summary.csv` | metrics `cheapest_first_year_usd` (1.54) and `n_tlds_first_year_lt_2usd` (36) | MINT |
| "The largest burn ratio" | names exposed "in public Certificate Transparency (CT) logs" | `data/minting/derived/exposure_channels.csv` | rows "CT log, static-ct-api ..." and "CT log, RFC 6962" | file |
| "Public data ground these ingredients" | "China has blocked `workers.dev` suffix-wide" | `data/burn_units/derived/burn_units.csv` | row CN `workers.dev`, `granularity` `mixed (tenant, then suffix)` and `suffix_date` 2022-04-30 | BURN |
| "Public data ground these ingredients" | "and Iran `pages.dev`" | `data/burn_units/derived/burn_units.csv`, `data/burn_units/derived/ir_irblock_platform_summary.csv` | row IR `pages.dev`, `granularity` `suffix-wide rule`. `irb_bare_blocked` True | BURN |
| "Public data ground these ingredients" | "yet both block `github.io` tenants one name at a time" | `data/burn_units/derived/burn_units.csv` | rows CN and IR `github.io`, `granularity` `per-name (tenant)` | BURN |
| "Public data ground these ingredients" | "When Fastly ended support in March 2024 for the domain fronting used for Snowflake's rendezvous" | `data/snowflake/derived/event_table.csv` | `event_id` `Fastly-2024-03-01`, column `start` (2024-03-01, from the Tor Metrics timeline, set in `event_list()` of `data/snowflake/analysis.py`) | SNOW |
| "Public data ground these ingredients" | "estimated Snowflake users worldwide fell 32.5% within a week" | `data/snowflake/derived/event_table.csv` | `Fastly-2024-03-01`, country `ALL`, columns `chg_primary_low_pct` (-32.51), `pre_low` (48,046.5) and `during_low` (32,428.0) | SNOW |
| "Public data ground these ingredients" | "while the number of proxy addresses barely changed" | `data/snowflake/derived/event_broker_metrics.csv` | `Fastly-2024-03-01`, country `ALL`, metric `ips_total`, column `chg_pct` (-2.143) | SNOW |
| contributions | "An exact solver and an event-driven simulator ... as an open testbed" | `simulations/code/exact.py`, `simulations/code/rotation_game.py` | the solver, and the generic birth-death simulator `_simulate_birth_death` | |

## 2 Background and Related Work

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| Timing games and moving-target defense | "Only minting replenishes the pool of live names, so availability depends on a birth-death process for that pool, coupled to the address layer through reachability" | `simulations/code/exact.py` | `name_rates_constant`: the pool K gains a name only by a mint (`lam_intro`, while K < k_max) and loses one by a burn (`lam_disc`). `interval_availability` multiplies the pool's window by the address window `addr_window` | |
| Game-theoretic proxy distribution | in Nasr et al.'s simulations "a system is eventually blocked below a critical arrival rate of new proxies" | `data/literature/derived/params_table.csv` | row N03 (an equilibrium arrival rate of about 3 proxies per day in their setting) | LIT |
| Game-theoretic proxy distribution | Fares et al. "find that the arrival rate of proxies relative to users matters more than the censor's strategy" | `data/literature/derived/params_table.csv` | row F01 | LIT |
| Game-theoretic proxy distribution | "Snowflake's rendezvous is such a channel, and it depends on names" | `data/snowflake/derived/` | see Section 6.2 | SNOW |
| Game-theoretic proxy distribution | "The resulting minting condition ... is the name-layer counterpart of Nasr et al.'s critical arrival rate" | `data/literature/derived/params_table.csv` | row N03 | LIT |

## 3 Threat Model and Scope

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| Position and capabilities | "The TSPU switched to SNI-based censorship of QUIC between May 2022 and July 2023" | `data/literature/derived/params_table.csv` | row T10 | LIT |
| Position and capabilities | "the GFW has filtered QUIC by SNI since 7 April 2024" | `data/literature/derived/params_table.csv` | rows G32 (date) and G31 (by SNI, regardless of the server address) | LIT |
| Position and capabilities | the censor finds endpoints "by classifying traffic, probing suspected servers and harvesting distribution channels" | `data/literature/derived/params_table.csv` | rows G09 and G50 (classification of fully encrypted traffic), G01 and G04 (probing), G27 and G46 (default bridges blocked after release). The channel-harvesting work cited with them is not in this table | LIT, file |
| Position and capabilities | the censor "may learn a name before any client uses it, for example from CT logs" | `data/minting/derived/exposure_channels.csv` | the two CT rows, `delay_min_s` and `delay_max_s` | file |
| Blocks persist | "The GFW's national name blocks last a median of at least 256 days" | `data/literature/derived/params_table.csv`, `data/literature/derived/derived_values.csv` | row G43 (median 256 days, equal to the window length, so a lower bound). Row `gfw_name_block_median_lower_bound_days` of `derived_values.csv` (`>=256`) | LIT, file |
| Blocks persist | "lapses, as at Henan's regional firewall, only help the defender" | `data/literature/derived/params_table.csv` | rows G43 (Henan median 21 days) and H03 (Henan adds and removes suffix rules) | LIT |
| Blocks persist | "The GFW renews it during use and lifts it about 12 hours after the service stops" | `data/literature/derived/params_table.csv` | rows G18 and G19 | LIT |
| Discovery is an effective rate | the GFW applies its filter for fully encrypted traffic "only to connections toward certain data-center ranges, and to only about a quarter of those" | `data/literature/derived/params_table.csv` | row G50 (26% of connections, specific data-center ranges) | LIT |
| Scope | "WebTunnel bridges by default use the operator's domain name with a publicly trusted certificate" | `data/minting/derived/doc_facts.csv` | facts `tor_wt_requires_domain` ("a domain under your control") and `tor_wt_requires_cert` ("A valid TLS certificate;"), from the WebTunnel guide, which obtains the certificate with an ACME client | MINT |
| Scope | "a pinned certificate with no SNI or, as WebTunnel supports, an arbitrary one" | `data/minting/derived/doc_facts.csv`, `data/burn_units/derived/qualitative_events.csv` | fact `tor_nonwebpki_pinning` (the pinned certificate). Row `tor-gitlab-40064` of `qualitative_events.csv` (Tor GitLab issue 40064), `quotes` with the reported bypass by setting `servername`, `quotes_verified` True, `date` 2025-06-23 | MINT, file |
| Scope | "a Snowflake client needs its rendezvous for every new proxy" | | a design statement of Bocovich et al. (2024), not produced here | |
| Out of scope | "as Russia did with Snowflake's Datagram TLS (DTLS) handshake" | `data/snowflake/derived/churn_published.csv` | claim `ru_2021_dtls_supported_groups`, columns `quote`, `verified_in_pdf_text` and `pdf_page` (quote found on PDF page 14 of Bocovich et al. 2024, Section 5.1) | SNOW |
| Out of scope | "Residual blocks, lasting seconds to minutes after a detected connection" | `data/literature/derived/params_table.csv` | rows G12 (120 or 180 s), G33 (180 s), T06 (40 to 420 s) and I03 (60 s) | LIT |

## 4 Model

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| after Definition 4.1 | the burn rate "is an aggregate rate that does not grow with K (Appendix C relaxes this)" | `simulations/code/exact.py`, `R10_perunit_normalization.json` | `name_rates_constant`, whose death rate is `lam_disc` in every state K >= 1. The per-name pool of Appendix C, whose burn rate grows with K, is `name_rates_perunit` (death rate delta K), with its frontier in R10 (see Appendix C below) | SIM |
| after Definition 4.1 | "The product form of Theorem 5.1 assumes that any live name can reach any unblocked endpoint, as when every endpoint accepts every live name, and that the layers are independent" | `simulations/code/exact.py`, `simulations/code/rotation_game.py` | the solver multiplies the layers, `interval_availability` = `name_window_constant` x `addr_window` and `timeavg_availability` = (1 - pi_0) c_a, and counts the system as up when K >= 1 and one endpoint is unblocked. The simulator draws the layers on independent clocks and takes the union of their down intervals (`combine`) | |
| after Definition 4.1 | "Pairing names with particular endpoints never raises availability and leaves the cap of Theorem 5.2 intact" | | an analytic statement. No code pairs names with endpoints, since the solver and the simulator let every live name reach every unblocked endpoint | |
| Lemma 4.3 | each endpoint is blocked with probability p = lambda_a/(lambda_a + mu), and all n with p^n | `R1_exact_validation.json`, output of `exact.py` | `E1.stats` (simulation against p^n at 40 points, largest difference 0.0014). Self-test line "address stationary P[c=0] = p^n: ok" | EXACT, file |
| Remark 4.4 | "At mu = 3 lambda_a and n = 8 this is 0.040" | `R7_sync_discovery.json` | `rows (n = 8, s = 1.0).P_c0` (0.0400, equal to `sweep_closed_form`) | SIM |
| Remark 4.4 | "against p^n = 1.5 x 10^-5 under independent discovery" | `R7_sync_discovery.json` | `rows (n = 8, s = 0.0).p_pow_n` (1.526e-5) | SIM |
| Remark 4.4 | the address layer stays up throughout T = 5 "with probability 0.998 under independent discovery but only 0.949" at a sweep share of 1% | `R7_sync_discovery.json` | `rows (n = 8, s = 0.0).addr_window_T5` (0.9982) and `rows (n = 8, s = 0.01).addr_window_T5` (0.9492). Also `canonical_consequences` | SIM |
| Proposition 4.5 | the stationary law and pi_0 of the name pool | output of `exact.py` | self-test line "LinearCTMC(batch b=1) == birth-death pool: ok", which compares a separately built chain with the birth-death pool and with 1 - pi_0 | EXACT |

## 5 Analysis

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | the canonical configuration (n = 8, lambda_a = lambda_intro, mu = 3 lambda_a, k_max = 8, alpha = 0.95, T = 5) | every R file | `_meta.canonical` | file |
| opening | "This illustrative configuration assumes that addresses are discovered on the timescale of minting" | every R file, `R13_rotation_speed.json` | `_meta.canonical`: `lam_a` = `lam_intro` = 1. R13 relaxes it for Section 5.3 (`lam_a_over_lam_intro` 1, 10 and 60) | file |

### 5.1 Closed-Form Availability and the Burn Cap

Section 5.1 reports no computed numbers. Appendix A proves Theorem 5.1, and
Section 5.1 proves Theorem 5.2.

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| before Theorem 5.2 | "The cap below is an impossibility result. Its bound 1/beta needs neither independent layers nor Poisson events (Proposition A.3)" | | analytic, see Proposition A.3 under Appendix A below | |

### 5.2 The Sustainability Frontier

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| Theorem 5.3 | (iv) "beta*(alpha,T) is nondecreasing in k_max, n and mu" | `R2_frontiers.json`, `R13_rotation_speed.json` | proved in Appendix A. In k_max, `interval_beta_star_nondecreasing_in_kmax` (true) of R2, over the 120 frontiers of its `table`. In mu and n, `beta_star_interval` of the 18 R13 rows (n = 4, 8 and 16) falls by at most 2.5e-12, which is rounding, along `ratios_mu_over_lam_a`, and never from n = 4 to 8 to 16 at equal `kmax`, `lam_a_over_lam_intro` and mu/lam_a, with null (no beta meets the target) counted as below every frontier (line "Thm. 5.3") | SIM |
| after Proposition 5.4 | "Both factors thus need exponentials of matrices with at most max{n,k_max} rows" | `simulations/code/exact.py` | `bd_window` evaluates pi_U e^{Q_UU T} 1 with the generator restricted to the up states 1..m (`_bd_killed_tridiag`), m = n for `addr_window` and m = k_max for `name_window_constant`, by the eigenpairs of the symmetrized matrix up to 200 states (see Appendix B, Numerical method) | |
| after Proposition 5.4 | window probabilities "computed to about 10^-12" | output of `exact.py` | 1.99e-14 and 4.44e-15 (see Appendix B, Accuracy) | EXACT |
| after Proposition 5.4 | "a root beta* takes milliseconds" | output of `extra_values.py` | line "Section 7, one exact interval frontier at k_max = 8" (6.5 to 9.1 ms on the reference workstation) | EXTRA |
| after Proposition 5.4 | the simulator "agrees with the exact values within Monte Carlo error where standard errors are available, and to within 0.009 elsewhere" | `R1_exact_validation.json` | `E2.stats_interval.frac_within_3se` (0.993). The `summary` entries `*_max_abs_diff` other than `E2_interval_max_abs_diff`, the largest being `E3_interval_max_abs_diff` (0.0086) | SIM |
| Exact frontiers | "beta*_avg = 0.257, 0.577, 0.840, 0.980 and 1.035 for k_max = 2, 4, 8, 16 and 32" | `R2_frontiers.json` | `dense.avg["0.95"] @ k_max = 2, 4, 8, 16, 32`. Cross-check in `data/literature/derived/frontier_sensitivity.csv`, rows alpha 0.95, n 8, `mu_over_lambda_a` 3.0, `beta_star_avg` 0.5766, 0.8397, 0.9804 and 1.0353 for k_max = 4 to 32 | SIM |
| Exact frontiers | "tending to c_a/alpha = 1.053" | `R2_frontiers.json` | `c_a` / 0.95 (`c_a` = 0.999985) | SIM |
| Exact frontiers | "beta*(0.95,5) = 0.098, 0.355, 0.661, 0.865 and 0.963 for the same buffers" | `R2_frontiers.json` | `dense.interval["0.95\|5.0"] @ k_max = 2, 4, 8, 16, 32` | SIM |
| Exact frontiers | "W^addr_5 = 0.998 here, so the name pool sets beta*" | `R2_frontiers.json` | `address_window["5.0"]` (0.99825) | SIM |
| Exact frontiers | the interval frontier "exceeds 1 from k_max = 63 on" | `R2_frontiers.json` | `min_kmax_beta_star_above_1["0.95"]["5.0"].kmax` (63) | SIM |
| Exact frontiers | "and tends to 1.016" | `R2_frontiers.json` | `large_kmax_interval_beta_star["0.95"]["5.0"]["8192"]` (1.01624, the same to 1e-12 from k_max = 2048 on) | SIM |
| Exact frontiers | "The smallest buffer with beta* > 1 grows with the window length (Figure 1) and with the target" | `R2_frontiers.json` | `min_kmax_beta_star_above_1["0.95"]`: 34, 43, 63, 87 and 128 for T = 1, 2, 5, 10 and 20. `min_kmax_beta_star_above_1["0.9"]`, `["0.95"]` and `["0.99"]`, each at `["5.0"].kmax`: 31, 63 and 369 | SIM |
| Exact frontiers | "At k_max = 8, beta*(0.95,T) = 0.755, 0.661, 0.610 and 0.552 for T = 1, 5, 10 and 20" | `R2_frontiers.json` | `table` rows (alpha = 0.95, kmax = 8, T = 1, 5, 10, 20), `beta_star_interval` | SIM |
| Figure 1 | the time-average frontier and the interval frontier for T = 1, 5 and 20 against k_max | `figures/frontier.pdf` | drawn from `R2_frontiers.json`, `dense.avg["0.95"]` and `dense.interval["0.95\|1.0"]`, `["0.95\|5.0"]` and `["0.95\|20.0"]` for k_max <= 256. The checks compare the curves with `exact.py` at k_max = 2, 4, 8, 32, 128 and 256 | FIG |
| Figure 1 caption | circles at "k_max = 20, 34, 63 and 128" | `R2_frontiers.json` | `min_kmax_beta_star_above_1["0.95"]`: `time_average` (20) and `"1.0"`, `"5.0"`, `"20.0"` `.kmax` (34, 63, 128) | SIM |
| Figure 1 caption | "The dotted line is the bound c_a/alpha = 1.053" | `R2_frontiers.json` | `c_a` / 0.95 | SIM |
| Figure 1 description | the curves "rise steeply from between 0.05 and 0.26 at a buffer of 2" | `R2_frontiers.json` | `dense @ k_max = 2`: 0.048 (T = 20) to 0.257 (time average) | file |
| Figure 1 description | they "level off just above 1, with longer sessions lower" | `R2_frontiers.json` | `dense @ k_max = 256`: 1.053 (time average), 1.030, 1.016 and 1.006 (T = 1, 5, 20) | file |
| Figure 2 | "Lines are exact values" | `figures/phase.pdf` | recomputed with `exact.py`, equal to `R1_exact_validation.json` `E2.per_kmax[k].exact_interval` at the 37 E2 betas (largest difference 0) | FIG |
| Figure 2 | "markers event-driven simulations (k_max <= 32)" | `E2_phase_transition.json` | `curves["4"/"8"/"16"/"32"].interval`, plotted at beta = 0.2, 0.3, ..., 2.0 (every second of the 37 betas) | FIG |
| Figure 2 | "with two-standard-error bars smaller than the markers" | output of `make_figures.py` | check "error bars (2 SE) shorter than the marker radius": largest 2 SE 0.0074 (0.94 pt) against a marker radius of 1.65 pt, with SE from `E2_phase_transition.json` `curves[k].interval_std` / sqrt(24) | FIG |
| Figure 2 description | "The buffer-8 curve crosses the dotted 0.95 target line near a burn ratio of 0.66 and the buffer-64 curve near 1" | `R2_frontiers.json` | `dense.interval["0.95\|5.0"] @ k_max = 8` (0.661) and `@ k_max = 64` (1.0009) | file |
| Figure 2 description | "At a burn ratio of 2 all curves are at about 0.05 or below" | output of `extra_values.py` | line "Figure 2": 0.027, 0.050, 0.052, 0.052 and 0.052 for k_max = 4, 8, 16, 32 and 64 | EXTRA |
| Figure 2 description | "Simulation markers lie on the exact lines" | `R1_exact_validation.json` | `E2.stats_interval.max_abs_diff` (0.0052) | SIM |
| after the figures | "at k_max = 8 and beta = 1 the time-average availability is 0.889 but A_T = 0.659" | `R4_strategic_censor.json` | `policies["8"].poisson.timeavg_at_beta["1.0"]` (0.8889) and `.interval_at_beta["1.0"]` (0.6594). The same values are in `R5_diversification.json` `by_kmax["8"].single_pool_unit_burns` | SIM |

### 5.3 When Rotation Speed Matters

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "At n = 8 and mu/lambda_a = 1, c_a = 0.996" | `R13_rotation_speed.json` | `rows (n = 8, kmax = 8, lam_a_over_lam_intro = 1).c_a @ mu/lam_a = 1` (0.99609). Cross-check in `data/literature/derived/frontier_sensitivity.csv`, row alpha 0.95, n 8, `mu_over_lambda_a` 1.0, `c_a` 0.996094 | SIM |
| opening | "W^addr_T is 0.872 for lambda_a T = 5" | `R13_rotation_speed.json` | the same row, `addr_window_T5 @ mu/lam_a = 1` (0.8718). `extra_values.py` prints it too | SIM |
| opening | "0.669 for lambda_a T = 15 and 0.204 for lambda_a T = 60" | output of `extra_values.py` | lines "mu/lambda_a = 1, lambda_a T = 15" and "mu/lambda_a = 1, lambda_a T = 60" | EXTRA |
| opening | the value of beta*(0.95,5) for a perfect address layer, "(0.665)" | `R13_rotation_speed.json` | `rows (n = 8, kmax = 8, ...).beta_star_interval_limit_mu_inf` (0.66521) | SIM |
| opening | "once mu/lambda_a >= 2.52, 4.00 and 5.66 for lambda_a T = 5, 50 and 300 (lambda_a = lambda_intro, 10 lambda_intro and 60 lambda_intro)" | `R13_rotation_speed.json` | `rows (n = 8, kmax = 8, lam_a_over_lam_intro = 1, 10, 60).saturation_ratio_interval["0.01"]` (2.520, 4.000, 5.657), with `lam_a_T` 5, 50 and 300 | SIM |
| opening | "For the time-average frontier the threshold is about 1.12 for any lambda_a" | `R13_rotation_speed.json` | `saturation_ratio_timeavg["0.01"]` (1.1225 in all three rows) | SIM |
| opening | "These thresholds are grid values, at most 7% above the true ones" | `R13_rotation_speed.json`, output of `extra_values.py` | `ratios_mu_over_lam_a` (49 points from 0.5 to 128, step 2^(1/6) = 1.1225) and `definition`. `extra_values.py` prints the exact thresholds, 2.472, 3.913 and 5.408 (interval, lambda_a T = 5, 50 and 300) and 1.055 (time average), which the grid values exceed by 1.9%, 2.2%, 4.6% and 6.4%, so by at most 6.4% (line "mu/lambda_a at which beta* comes within 0.01 of its limit") | SIM, EXTRA |
| opening | "Faster rotation then moves it by less than 0.01" | `R13_rotation_speed.json` | `definition` (the saturation ratio is where beta* stays within tol = 0.01 of the limit). Between grid points this holds because beta* never falls as mu grows (Theorem 5.3, see Section 5.2) | file |
| opening | "At the canonical mu/lambda_a = 3 this happens once lambda_a > 29.5 lambda_intro" | `R13_rotation_speed.json` | `timescale_caveat_canonical.lam_a_over_lam_intro_where_window_equals_alpha` (29.52) | SIM |
| Wall-clock timescales | "For Tor bridges that the GFW confirms by active probing, blocks follow on the order of minutes, although no source reports a mean" | `data/literature/derived/params_table.csv`, `data/literature/derived/address_layer_mapping.csv` | rows G03, G45, G01, G04 and G44. Scenario `gfw_tor_dpi_probe` of `address_layer_mapping.csv`, `E_D_a_seconds` 1 (lo), 60 (central) and 300 (hi) | LIT, file |
| Wall-clock timescales | "relays listed in the public Tor consensus were blocked after about 10 minutes" | `data/literature/derived/params_table.csv`, `data/literature/derived/address_layer_mapping.csv` | row G26. Scenario `gfw_published_directory`, `E_D_a_seconds` 600 | LIT, file |
| Wall-clock timescales | "Taking a mean time to block of one minute ..., a one-hour session has lambda_a T = 60", and a one-day session lambda_a T = 1440 | `data/literature/derived/address_layer_mapping.csv` | scenario `gfw_tor_dpi_probe`, bound `central`, `E_D_a_seconds` 60. 3600 / 60 = 60 and 86400 / 60 = 1440, the ratios of its columns `lambda_a_dimless_tau_1 h` and `lambda_a_dimless_tau_1 d` | file |
| Wall-clock timescales | "W^addr_T then reaches 0.95 only if mu/lambda_a >= 2.49, a rotation about every 24 s per endpoint" | output of `extra_values.py` | line "one-hour session (lambda_a T = 60)" | EXTRA |
| Wall-clock timescales | "A one-day session (lambda_a T = 1,440) needs mu/lambda_a >= 4.63, a rotation about every 13 s" | output of `extra_values.py` | line "one-day session (lambda_a T = 1440)" | EXTRA |
| Wall-clock timescales | "Both are stress tests that provider quotas may rule out" | output of `extra_values.py` | an interpretation of the two lines above. A rotation every 24 s or 13 s per endpoint means, across the n = 8 endpoints, a new address about every 3.0 s or 1.6 s, about 29,000 or 53,000 a day. The repository records quotas on names, deployments and certificates (`names_per_account` of `data/minting/derived/platform_names.csv`, and facts such as `vercel_deploys_day`, `gcr_1000_services` and `gts_neworder` of `data/minting/derived/doc_facts.csv`), but no provider's limit on new addresses | EXTRA |

### 5.4 Beyond the Constant-Rate Censor

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "the constant-rate frontier is 0.661" | `R2_frontiers.json` | `dense.interval["0.95\|5.0"] @ k_max = 8` (0.6613). The same in `R4_strategic_censor.json` `policies["8"].poisson.beta_star_interval` and `R8_mint_exposure.json` `table["8"]["inf"]["0.0"]` | SIM |
| Mint-time exposure | a name can become visible at mint "when its certificate is logged in CT" | `data/minting/derived/doc_facts.csv` | facts `chrome_ct_required`, `apple_ct_required`, `le_logs_everything` and `rfc6962_precert` | file |
| Mint-time exposure | "At theta = infinity, beta* = 0.510, 0.352, 0.185 and 0.078 for rho = 0.25, 0.5, 0.75 and 0.9" | `R8_mint_exposure.json` | `table["8"]["inf"]["0.25"/"0.5"/"0.75"/"0.9"].beta_star_interval` | SIM |
| Mint-time exposure | "no beta suffices at rho = 1" | `R8_mint_exposure.json` | `table["8"]["inf"]["1.0"].status` ("none") | SIM |
| Strategic block timing | censors "delay and batch blocks ..., as the GFW apparently did with the Tor Browser default bridges of each release in 2015-16" | `data/literature/derived/params_table.csv` | rows G27 (blocking delays per release batch), G28 (all bridges of a batch blocked at once, within 20 minutes) and G47 (manual discovery after an unpredictable delay, then periodic automatic enforcement) | LIT |
| Strategic block timing | strike-all "lowers beta* from 0.661 to 0.064 and beta*_avg from 0.840 to 0.313" | `R4_strategic_censor.json` | `policies["8"].poisson` and `.strike_all`, `beta_star_interval` and `beta_star_timeavg` | SIM |
| Strategic block timing | the MDP "gives strike-all as the exact time-average best response at all 17 points solved" | `R4_strategic_censor.json` | `best_response_timeavg_mdp.rows` (17 rows, `optimal_policy_equals_strike_all` true in all) | SIM |
| Strategic block timing | "Fixed batches of two or four names barely move beta* (0.671 and 0.647)" | `R4_strategic_censor.json` | `policies["8"].batch_j2.beta_star_interval` (0.6712) and `.batch_j4` (0.6469) | SIM |
| Strategic block timing | "A defense is a reserve of r of the live names, unexposed at mint and served only once all names in use are blocked" | `simulations/code/exact.py`, `R4_strategic_censor.json` | `strategic_chain(kmax, policy, r=r)`: in its states (A, R, D), A + R <= k_max, so the r reserve names are part of the buffer of k_max live names. A mint joins the reserve while names are in use and the reserve holds fewer than r, reserve names are never served and so never discovered, and they become the active pool once it is empty. Its frontiers are `reserve["8"]` | |
| Strategic block timing | a reserve "has no effect on the constant-rate censor" | `R4_strategic_censor.json`, output of `exact.py` | `reserve["8"].poisson["0"/"1"/"2"/"4"].beta_star_interval` (all 0.6613). Self-test line "strategic('poisson', r=2) == constant pool: ok" | EXACT, file |
| Strategic block timing | "but against strike-all it raises beta* to 0.237, 0.367 and 0.522 for r = 1, 2 and 4" | `R4_strategic_censor.json` | `reserve["8"].strike_all["1"/"2"/"4"].beta_star_interval` | SIM |
| Correlated takedowns and diversification | "Bursts lower the frontier to beta* = 0.523, 0.314 and 0.066 for b = 2, 4 and 8" | `R1_exact_validation.json` | `E7.per_b["2"/"4"/"8"].beta_star_exact_root` | SIM |
| Correlated takedowns and diversification | "P = 1, 2, 4 and 8 providers gives beta* = 0.008, 0.092, 0.311 and 0.661" | `R5_diversification.json` | `by_kmax["8"].P["1"/"2"/"4"/"8"].pooled.beta_star_interval` | SIM |
| Correlated takedowns and diversification | diversification "recovers the single pool with unit burns when each provider holds one name, and never exceeds it" | `R5_diversification.json`, output of `exact.py` | `by_kmax["8"].P[P].pooled.max_excess_over_single_interval` (negative for P = 1, 2, 4 and 2.8e-15 for P = 8) and `pooled_beta_star_nondecreasing_in_P` (true). Self-test line "providers(P=8,kp=1,pooled) == constant pool: ok" | EXACT, file |

## 6 Grounding the Model in Public Data

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "We make no new measurements and draw on the literature and on public data, such as the measurements of ... (OONI)" | `data/burn_units/raw/manifest.json`, `data/snowflake/raw/manifest.json`, `data/literature/raw/manifest.json`, `data/minting/raw/manifest.json` | the URL of every input: public dataset APIs, file hosts, papers and documentation pages (see Appendix D below) | file |

### 6.1 Which Name Each Censor Burns

The opening paragraph and Table 1.

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "Table 1 classifies 19 platform suffixes for China, Iran and Russia" | `data/burn_units/derived/burn_units.csv` | 57 rows, one per `censor` and `platform` | BURN |
| opening | "Russia's registry entries are legal orders, and OONI measures too few platform entries to confirm their enforcement" | `data/burn_units/derived/run_meta.json`, `data/burn_units/derived/ru_ooni_vs_registry.csv` | `ru_registry_listed_low_coverage`: 88 registry-listed names on 9 platforms with at most 2 valid OONI measurements each, 43 in all, 0 anomalous. Rows with `registry_listed` True, `names` and `names_eligible`: 2 of the 118 OONI-measured listed names have 3 or more | BURN, file |
| Table 1 | the cells | `data/burn_units/derived/burn_units.csv` | `granularity`, with the year of `suffix_date`. 56 cells follow `granularity`, and the China cell of `azurefd.net` is in the next row. `data/burn_units/derived/README.md` explains how the typeset table differs from `burn_units_table.tex` | BURN |
| Table 1 | China `azurefd.net`, per-name blocks with the triangle | `data/burn_units/derived/cn_gfwatch_platform_summary.csv`, `data/burn_units/derived/run_meta.json` | `gfw_class` `tenant` (2 tenants). `azurefd_episode` | BURN |
| Table 1 caption | "Observed or ordered granularity of name blocks under 19 platform suffixes" | `data/burn_units/derived/burn_units.csv` | `granularity` of the 57 rows. The China and Iran cells rest on observed blocks, the Russia cells on registry entries, which order blocks (`evidence`) | BURN |
| Table 1 caption | "from GFWatch and OONI data for China, IRBlock scans for Iran (block onsets unknown) and registry dumps for Russia" | `data/burn_units/derived/burn_units.csv` | `evidence`, `first_date_meaning` | file |
| Table 1 caption | "Registry entries are legal orders, not proof of enforcement" | `data/burn_units/derived/run_meta.json`, `data/burn_units/derived/ru_ooni_vs_registry.csv` | `ru_registry_listed_low_coverage`, as in the opening paragraph above | BURN |
| Table 1 legend, per-name blocks | the seven China cells that "rest on GFWatch data to September 2024 alone, as OONI tested fewer than five of their tenant names in 2026" | `data/burn_units/derived/ooni_platform_summary.csv` | censor CN, `ooni_tested`: `pages.dev` 4, `netlify.app` 1, `onrender.com` 0, `fly.dev` 0, `deno.dev` 1, `firebaseapp.com` 0, `azurewebsites.net` 3 (host names) | BURN |
| Table 1 legend, suffix-wide rule | "in Russia, a registry entry" | `data/burn_units/derived/ru_registry_platform_summary.csv` | `reg_suffix_entry` (`pages.dev`) | BURN |
| Table 1 legend, per-name blocks then a suffix-wide rule | "Years give the rule's onset (for China, in GFWatch), and <='20 means in place when those data begin in March 2020" | `data/burn_units/derived/cn_gfwatch_platform_summary.csv`, `data/burn_units/derived/ru_registry_platform_summary.csv` | `gfw_suffix_onset` and `gfw_onset_left_censored`: `workers.dev` 2022-04-30, `vercel.app` 2022-08-26, `herokuapp.com` 2022-10-11, `appspot.com` 2020-03-20 (left-censored). Russia `pages.dev`, `reg_first_snapshot_suffix` 2024-05-09 | BURN |
| Table 1 legend, triangle | "Temporary impairment of tested names, trigger undetermined" | `data/burn_units/derived/run_meta.json`, `data/burn_units/derived/ooni_cn_monthly.csv`, `data/burn_units/derived/ooni_cn_azurefd_daily.csv`, `data/burn_units/derived/burn_units.csv` | `azurefd_episode`: 39 endpoints, 2025-08-02 to 2026-09-04, 64.6% of 2,551 measurements anomalous, 0.4% of 240 from 2026-09-05. Monthly rows of `azurefd.net`: names blocked 159 of 172 (July 2026), 166 of 177 (August), 6 of 166 (September). The daily series. `notes` of CN `azurefd.net` | BURN |
| Table 1 legend, ? | "Too few tenant names known to be tested, and no suffix-wide rule seen" | `data/burn_units/derived/burn_units.csv`, `data/burn_units/derived/tranco_bare_suffix_ranks.csv` | `granularity` `insufficient coverage` and `notes` (4 cells in China, 12 in Iran). `bare_rank` | BURN |
| Table 1 legend, empty set | "No registry entry. Blocking outside the registry is not covered" | `data/burn_units/derived/burn_units.csv`, `data/burn_units/derived/ru_registry_platform_summary.csv`, `data/burn_units/derived/ru_antifilter_platform_summary.csv` | `granularity` `none observed` (`r2.dev`, `trycloudflare.com`, `fly.dev`, `*.lambda-url.*.on.aws`). `reg_tenants` 0 and `reg_suffix_entry` False. `af_entries` 0 | BURN |
| Table 1 legend, double dagger | "Wildcard entry, enforcement unconfirmed by OONI" | `data/burn_units/derived/ru_registry_platform_summary.csv`, `data/burn_units/derived/ru_registry_timeseries.csv`, `data/burn_units/derived/ooni_platform_summary.csv` | `*.pages.dev`: `reg_suffix_decision_date` 2024-05-06, absent from the dump of 2024-05-06 (`reg_last_snapshot_without_suffix`) and present in that of 2024-05-09 (`reg_first_snapshot_suffix`). `suffix_entry`. RU `pages.dev`: `ooni_names_any` 14, `ooni_tested` 0, `ooni_bare_meas` and `ooni_bare_share` (0 of 90 anomalous) | BURN |
| Table 1 legend, asterisk | "In 2026 the bare suffix and Heroku's routing names are largely not blocked" | `data/burn_units/derived/ooni_platform_summary.csv`, `data/burn_units/derived/run_meta.json` | CN `herokuapp.com` `ooni_bare_meas` and `ooni_bare_share` (2 of 17 anomalous). `cn_heroku_routing`: 17 of 18 routing names clear, 1 intermittent, 357 of the other 358 names blocked | BURN |

The paragraph after Table 1.

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| after Table 1 | "In China, GFWatch recorded 259 blocked `github.io` tenants but no suffix rule" | `data/burn_units/derived/cn_gfwatch_platform_summary.csv` | `github.io`: `gfw_tenants` 259, `gfw_suffix_rule` False | BURN |
| after Table 1 | "and in 2026 OONI found 6 of 980 tested names blocked" | `data/burn_units/derived/ooni_platform_summary.csv` (also `burn_units.csv`, `n_blocked` and `n_tested`) | CN `github.io`, `ooni_blocked` and `ooni_tested` | BURN |
| after Table 1 | "Iran blocked 27 `github.io` tenants by name" | `data/burn_units/derived/ir_irblock_platform_summary.csv` | `github.io`: `irb_any_tenants` 27, `irb_bare_blocked` False | BURN |
| after Table 1 | "Russia's registry listed 30 `cloudfront.net` tenants at the end of 2021 and 10,224 in October 2025" | `data/burn_units/derived/ru_registry_timeseries.csv` | `cloudfront.net`, `tenants` by `snapshot` (30 on 2021-12-31, 10,224 on 2025-10-01) | BURN |
| after Table 1 | "China's DNS rules covered `workers.dev`, `vercel.app` and `herokuapp.com` in 2022" | `data/burn_units/derived/cn_gfwatch_platform_summary.csv` | `gfw_suffix_onset` (2022-04-30, 2022-08-26, 2022-10-11) | BURN |
| after Table 1 | "at least 405, 42 and 771 days after their first tenant blocks" | `data/burn_units/derived/cn_gfwatch_platform_summary.csv` | `gfw_suffix_onset` minus `gfw_tenant_first` (first tenants 2021-03-21, 2022-07-15, 2020-08-31) | BURN |
| after Table 1 | "in 2026 OONI still found 984 of 1,100, 1,008 of 1,008 and 357 of 376 tested names under them blocked" | `data/burn_units/derived/ooni_platform_summary.csv` | CN, `ooni_blocked` and `ooni_tested` | BURN |

### 6.2 Names in a Peer-to-Peer System

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "Tor's broker counted a median of 148,719 unique proxy addresses per day from 28 September to 3 October 2026" | `data/snowflake/derived/sf_proxy_ips_summary.csv` | period `v2_post_gap`: `ips_total_median` 148,718.5 over `n_windows` 6 broker windows, `date_from`, `date_to`, `definitions` (`daily_unique_cleared_each_window`). Also `data/snowflake/derived/summary.json`, `proxy_periods.v2_post_gap` | SNOW |
| opening | "and half the 2023 pool turned over in about 20 hours" | `data/snowflake/derived/churn_published.csv`, `data/literature/derived/params_table.csv` | claim `half_pool_turnover_about_20h`: `value` 20, a published figure (Bocovich et al. 2024, Fig. 7 caption, January 2023), quote found on PDF page 12 (`verified_in_pdf_text`, `pdf_page`). Row S01 of `params_table.csv`, whose `context` dates the figure to January 2023 | SNOW, LIT |
| opening | "every method the broker counts" | `data/snowflake/derived/sf_broker_windows.csv`, `data/snowflake/derived/sf_rendezvous_recent_by_country_method.csv` | three poll counters, HTTP, AMP cache and SQS, named `client-http-count`, `client-ampcache-count` and `client-sqs-count` in the broker specification. Columns `http_polls`, `amp_polls` and `sqs_polls`, and column `method` | SNOW |
| opening | "uses a censor-visible name, namely a CDN front or the broker's own domain, Google's ... (AMP) cache, or Amazon's ... (SQS)" | `data/snowflake/derived/summary.json`, `data/snowflake/derived/churn_published.csv` | `rdsys.methods_at_last_commit`, the methods configured at the last settings version (for example `amp,http_fronted` for Russia and `http_fronted,sqs` for China). Design quotes `rendezvous_front_collateral` and `amp_rendezvous_collateral` (PDF page 5). The names per method and version are in `rdsys_circumvention_snowflake_config.csv`, columns `snowflake_fronts`, `snowflake_amp_fronts` and `snowflake_sqs_hosts` (not shipped) | SNOW-SUMMARY |
| Turkmenistan and Fastly | "When Turkmenistan blocked the default broker front for months from October 2021" | `data/snowflake/derived/event_table.csv`, `data/snowflake/derived/churn_published.csv` | `TM-front-2021-10`, column `start` (2021-10-24). Claims `tm_2021_10_24_front_block` and `tm_alt_front_confirmed_aug2022` (the quote "not until August 2022" on PDF page 16) | SNOW |
| Turkmenistan and Fastly | "estimated Snowflake users there fell from 28 to 2" | `data/snowflake/derived/event_table.csv` | `TM-front-2021-10`, country `tm`, columns `pre_low` (28.0) and `during_low` (2.0), the low bound of Tor Metrics' estimate as the median over the 14 valid days before (2021-10-10 to 2021-10-23) and over the valid days of 2021-10-24 to 2021-10-30 (`pre_valid_days`, `during_valid_days`) | SNOW |
| Turkmenistan and Fastly | "When Fastly ended domain fronting on 1 March 2024" | `data/snowflake/derived/event_table.csv` | `Fastly-2024-03-01`, column `start` (2024-03-01, from the Tor Metrics timeline). The timeline rows are in `timeline_snowflake_related.csv` (not shipped) | SNOW |
| Turkmenistan and Fastly | "the Fastly fronts in use failed together" | `data/snowflake/derived/summary.json`, `data/snowflake/derived/event_table.csv` | `rdsys_rendezvous_names.removal_bursts`, the entry dated 2024-03-02 00:43:46, with `n_names` 1 and reason `failure stated ('blocked'; Fastly fronts)`, whose `subject` states that Fastly fronts were blocked. This is the rdsys-admin commit `4d979dbb1e`. Column `layer` of the `Fastly-2024-03-01` rows (`rendezvous name (Fastly fronts in use)`) | file |
| Turkmenistan and Fastly | "Within a week, HTTP rendezvous polls fell 85.8%" | `data/snowflake/derived/event_broker_metrics.csv` | `Fastly-2024-03-01`, country `ALL`, metric `http_polls`: `chg_pct` -85.774, the median of the first 7 broker windows (2024-03-01 to 2024-03-07, 210,960) against the median of the 14 windows before (2024-02-16 to 2024-02-29, 1,482,920), columns `pre_median`, `during_median`, `pre_n`, `during_n` | SNOW |
| Turkmenistan and Fastly | "and estimated users 32.5%" | `data/snowflake/derived/event_table.csv` | `Fastly-2024-03-01`, country `ALL`, `chg_primary_low_pct` (-32.51) | SNOW |
| Turkmenistan and Fastly | "while proxy addresses fell only 2.1%" | `data/snowflake/derived/event_broker_metrics.csv` | `Fastly-2024-03-01`, country `ALL`, metric `ips_total`, `chg_pct` (-2.143, 146,928 to 143,780) | SNOW |
| Turkmenistan and Fastly | "Tor configured other fronts the same day" | `data/snowflake/raw/gitlab/rdsys-admin/circumvention_log.tsv` (download) | commit `4d979dbb1e`, authored 2024-03-01 20:57:26 UTC and committed 2024-03-02 00:43:46 UTC (`author_date`). The names it adds are the rows of that commit with action `added` in `rdsys_name_events.csv` (not shipped) | SNOW-TSV |
| Turkmenistan and Fastly | "yet HTTP polls regained half their earlier volume only after 36 days" | `data/snowflake/derived/summary.json` | `fastly_http_recovery.first_date_ge50pct` (2024-04-06, 36 days after 2024-03-01, the first window on or after 2024-03-02 with at least half of the median of 2024-02-16 to 2024-02-29) and `pre_median_2024_02_16_to_29` | SNOW |
| Turkmenistan and Fastly | "Its Connection Assist settings introduced 19 rendezvous names and retired 11 from 2022 to 2026" | `data/snowflake/derived/summary.json` | `rdsys_rendezvous_names`: `n_distinct` (19 fronts, AMP fronts and SQS hosts), `n_present_at_last_commit` (8), `first_added_by_year` (2022: 2, 2023: 3, 2024: 9, 2025: 2, 2026: 3). Per name in `rdsys_name_spans_all_countries.csv`, kinds `front`, `amp_front` and `sqs_host` (not shipped) | SNOW |
| Turkmenistan and Fastly | "A client needs a live name for each new proxy, so its session survival lies between A_T and A" | | follows from Definition 4.2 and from the design statement of Section 3 that a Snowflake client needs its rendezvous for every new proxy (Bocovich et al. 2024). Not computed here | |

### 6.3 Minting Economics and Exposure

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "On 3 October 2026, one registrar listed 36 top-level domains (TLDs) under $2 for the first year" | `data/minting/derived/porkbun_summary.csv` | metrics `n_tlds_first_year_lt_2usd` (36), `retrieved_utc` (2026-10-03T21:46:19Z) and `icann_tlds_priced` (543). Also `summary.json`, key `porkbun` | MINT |
| opening | "the cheapest at $1.54" | `data/minting/derived/porkbun_summary.csv` | metrics `cheapest_first_year_usd` (1.54) and `cheapest_first_year_tlds` (26 TLDs) | MINT |
| opening | "Let's Encrypt issues free certificates" | `data/minting/derived/doc_facts.csv` | fact `le_free` | MINT |
| opening | "and allows 2,400 orders a day per account" | `data/minting/derived/acme_mint_rates.csv` | row "Let's Encrypt, per ACME account", column `sustained_per_day` (2400 = 86,400 s / 36 s). Also `summary.json`, key `acme.le_orders_per_account_per_day`, and fact `le_orders_per_account` | MINT |
| opening | labels under an owned domain and tenant names within a per-account cap "count as free new names if the censor blocks exact names" | `data/minting/derived/minting_costs.csv` | column `marginal_cost_per_name_usd` (0.0) in the rows "sub-domain label under an owned domain" and "platform tenant sub-domain (PSL private suffix)". Column `censor_burn_unit` of the same rows: a label or tenant name is a name of its own only if the censor blocks exact names, and otherwise the parent domain or the platform suffix is one name | file |
| opening | "within a platform's per-account cap" | `data/minting/derived/platform_names.csv` | column `names_per_account`, with facts `gh_one_site`, `cf_workers_per_account`, `cf_pages_100_projects`, `vercel_projects`, `vercel_deploys_day`, `firebase_36_sites`, `deno_free_10_apps`, `azure_free_10_apps` and `gcr_1000_services` | file |
| exposure | "Publicly trusted certificates must be logged in CT for Chrome and Apple platforms to accept them" | `data/minting/derived/doc_facts.csv` | facts `chrome_ct_required` and `apple_ct_required` | MINT |
| exposure | "the logs commit to adding entries within 60 s or 24 h" | `data/minting/derived/summary.json` | `ct_log_list.mmd_values_static` ([60], in `n_static_usable_or_qualified` 43 logs), `ct_log_list.mmd_values_rfc6962` ([86400], in `n_rfc6962_usable_or_qualified` 21 logs) and `ct_log_list.log_list_version` (93.3). Also facts `rfc6962_mmd` and `chrome_incorporate_mmd`, and `exposure_channels.csv` (`delay_max_s` 60 and 86400) | MINT |
| exposure | "in 2018 third parties looked up new names 73 to 197 s after logging" | `data/minting/derived/scheitle2018_table4.csv` | column `dns_delay_s` (minimum 73, maximum 197, 11 rows). Also `summary.json`, keys `scheitle2018.dns_min_s` and `scheitle2018.dns_max_s`, and fact `scheitle_dns_73s_3min` | MINT |
| exposure | "New names in generic TLDs also appear in daily zone files" | `data/minting/derived/doc_facts.csv` | facts `zfa_daily`, `zfa_active_names` and `ra_icann_daily`. Also `exposure_channels.csv`, row "gTLD zone file (ICANN CZDS)" | MINT |
| exposure | only labels under a wildcard certificate, tenant names under a platform wildcard that are not otherwise published, and labels with a private pinned certificate "are unexposed at mint" | `data/minting/derived/minting_costs.csv`, `data/minting/derived/exposure_channels.csv` | column `exposed_at_mint` of every unit type, and the rows "Wildcard certificate (own domain or platform)", "Private-CA or pinned (non-WebPKI) certificate" and "GitHub public event timeline (GH Archive)". Facts `le_dns01_wildcard`, `rfc9525_one_label`, `gh_free_public_only`, `gh_createevent_repo`, `gh_event_repo_name` and `gh_events_latency` | file |
| exposure | "(as for `*.netlify.app` and `*.web.app`)" | `data/minting/derived/crtsh_platform_wildcards.csv` | rows with `identity_queried` `*.netlify.app` (DigiCert, 2026-02-16 to 2027-03-19) and `*.web.app` (Google Trust Services, 2026-07-20 to 2026-10-18). Column `ct_exposure_at_mint` of `platform_names.csv` explains why `*.github.io` is not named | MINT |
| exposure | "which WebTunnel has supported since 2025" | `data/minting/derived/doc_facts.csv` | fact `tor_nonwebpki_pinning` (Tor blog post of December 2025) | MINT |
| exposure | the exposed share is "near 1 for registrable generic-TLD domains and CT-logged names and near 0 for names that no channel exposes at mint" | `data/minting/derived/minting_costs.csv` | column `exposed_at_mint` | file |
| exposure | "The rate theta at which a censor burns exposed names is unmeasured" | | no source of this analysis measures it | |

## 7 Implications for Operators

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| step 2 | the lower bound 1 - p^n (1 + n mu T_wall) on the address window | output of `extra_values.py` | line "Appendix B, closed-form address bound after Corollary B.2": 0.99815 against the exact 0.99825 at the canonical configuration | EXTRA |
| step 3 | compute beta* "with the exact solver ... in about 8 ms per frontier at k_max = 8" | output of `extra_values.py` | line "Section 7, one exact interval frontier at k_max = 8" (6.5 to 9.1 ms on the reference workstation, depending on load), which calls `exact.frontier_interval` | EXTRA |
| step 3 | "If takedowns remove b names at once, use the frontier for that b" | `R1_exact_validation.json` | `E7.per_b[b].beta_star_exact_root` | SIM |
| step 4 | "Bisection in lambda_intro solves the rule, since more mints never leave fewer live names (Lemma A.2)" | `simulations/code/exact.py` | `frontier_interval(alpha, T, n, lam_a, mu, kmax, lam_intro)` takes rates in any common unit, so it returns beta*(alpha, lambda_intro T_wall) for wall-clock rates and T = T_wall, the value each bisection step needs. No script of the repository runs the bisection | |
| step 5 | "Keep a reserve of r of the live names, unserved and unexposed until the active pool is empty" | `simulations/code/exact.py` | `strategic_chain`, in which the reserve is part of the buffer (A + R <= k_max), as in Section 5.4 | |
| step 5 | a reserve "recovers part of the frontier lost to a strike-all censor and leaves it unchanged against a constant-rate censor" | `R4_strategic_censor.json` | `reserve["8"].strike_all` and `reserve["8"].poisson` | SIM |
| step 6 | "Prefer platforms whose tenant names the censor blocks one at a time (Table 1)" | `data/burn_units/derived/burn_units.csv` | `granularity` | BURN |
| step 6 | platforms used "within their quotas and terms of service" | `data/minting/derived/platform_names.csv` | columns `names_per_account` and `account_terms` | file |
| step 7 | "Censors differ in what they burn (Table 1)" | `data/burn_units/derived/burn_units.csv` | `granularity` | BURN |

## 8 Discussion

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| What the censor can do | "Most counter-moves map to a parameter and a defense" | `R2_frontiers.json`, `R8_mint_exposure.json`, `R4_strategic_censor.json` | an interpretation. Faster burning raises lambda_burn, against which step 4 of Section 7 sets the mint rate from the frontier (R2). Burning names exposed at mint is the share rho, with the frontiers of R8. Striking every name in use is the strike-all policy of R4, and `reserve["8"].strike_all` gives the frontiers with an unexposed reserve. The paragraph calls the other two, escalation to a suffix rule and range blocking in a crisis, regime changes | |
| What the censor can do | striking every name in use "lowers the frontier about tenfold at k_max = 8" | `R4_strategic_censor.json` | `policies["8"].poisson.beta_star_interval` / `.strike_all.beta_star_interval` = 0.6613 / 0.0641 = 10.3 | SIM |
| What the censor can do | "Escalation from tenant blocks to a suffix rule" | `data/burn_units/derived/burn_units.csv` | `granularity` `mixed (tenant, then suffix)` | BURN |
| Limits | "public sources record which names were blocked, not when a deployment minted them, and test popular or listed names" | `data/burn_units/SOURCES.md` | sources 1, 4 and 7 (GFWatch lists only blocked names, GFWatch and IRBlock test Tranco and other lists) | |
| Limits | "access-gated zone files of ICANN's Centralized Zone Data Service" | `data/minting/derived/doc_facts.csv` | facts `zfa_agreement` and `zfa_deny`. Also `exposure_channels.csv`, row "gTLD zone file (ICANN CZDS)", column `access` | MINT |

## 9 Conclusion

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| conclusion | "The required speed rises with the session length in mean discovery delays, and beyond it faster rotation barely moves the frontier" | `R13_rotation_speed.json` | rows (n = 8, kmax = 8, lam_a_over_lam_intro = 1, 10, 60): `saturation_ratio_interval["0.01"]` 2.520, 4.000 and 5.657 for `lam_a_T` 5, 50 and 300. Beyond it beta*(0.95,5) stays within 0.01 of `beta_star_interval_limit_mu_inf` (0.665), see Section 5.3 | SIM |
| conclusion | "Public data show that the unit a censor burns varies by censor and platform" | `data/burn_units/derived/burn_units.csv` | `granularity` (Table 1) | BURN |
| conclusion | "and that a peer-to-peer system still depends on names at rendezvous" | `data/snowflake/derived/` | see Section 6.2 | SNOW |

## Appendix A Proofs

Appendix A proves its results analytically and reports no computed numbers.
`python3 exact.py` (EXACT) checks two of the closed forms it proves, in the
self-test lines "address stationary P[c=0] = p^n: ok" (Lemma 4.3) and
"LinearCTMC(batch b=1) == birth-death pool: ok", which also compares the time
average with 1 - pi_0 (Proposition 4.5 and Lemma A.1). SIM checks the
monotonicity of Theorem 5.3(iv) in n and mu on the stored address windows and
frontiers (line "Thm. 5.3").

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | the appendix "proves Lemma 4.3, Theorems 5.1 and 5.3, and Propositions 4.5 and A.3" | | analytic | |
| proof of Theorem 5.3 | "a larger n or mu raises the birth rates mu(n-c) of the address chain, so W^addr_T, and with it beta*(alpha,T), is nondecreasing in n and mu" | `simulations/code/exact.py`, `R13_rotation_speed.json` | `addr_rates(n, lam_a, mu)`: births mu (n - c) and deaths lam_a c. In the 18 R13 rows, `addr_window_T5` falls by at most 1.1e-12, which is rounding, along `ratios_mu_over_lam_a` and never from n = 4 to 8 to 16, and `beta_star_interval` behaves the same way (line "Thm. 5.3", see Section 5.2) | SIM |
| Proposition A.3 | "the expected fraction of [0,t] with K >= 1 is at most 1/beta + o(1) as t -> infinity, and in stationarity A <= Pr[K >= 1] <= 1/beta" | `R10_perunit_normalization.json` | analytic, and no code checks it. Its proof first bounds the burns in [0,t] by the admitted mints plus k_max (B(t) <= M(t) + k_max), and in rate form its conclusion is lambda_burn Pr[K >= 1] <= lambda_intro. The stationary pools of the code show the bound as flow balance, since burns per mint interval equal the admitted mint rate and so stay below 1, for example `realized_burn_at_beta_star` in R10 (0.653 at the constant-rate frontier and 0.943 under per-name discovery) | file |

## Appendix B Exact Interval Availability

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| Remark B.1 | "the exponential gives p = 0.25 and a deterministic delay 0.05" | `R6_heavy_tail_discovery.json` | `rows` with `law` "exponential" and "deterministic", `p_quadrature` (0.2500, 0.0498, and `p_closed_form` agrees) | SIM |
| Remark B.1 | the hyperexponential law "gives 0.70, which leaves n = 8 endpoints with c_a = 0.945" | `R6_heavy_tail_discovery.json` | `rows` with `law` `hyperexp_0.9@0.1_0.1@9.1`: `p_quadrature` (0.6958) and `c_a_n8` (0.9450) | SIM |
| Remark B.1 | a deterministic delay minimizes p, and mixtures of exponentials give at least the value of a single exponential | `R6_heavy_tail_discovery.json` | `laws_with_p_below_exponential`, `laws_with_p_above_exponential` and `notes` | file |
| after Corollary B.2 | "At the canonical configuration it is 0.99815, against the exact W^addr_5 = 0.99825" | output of `extra_values.py` | line "Appendix B, closed-form address bound after Corollary B.2" | EXTRA |
| Numerical method | for the birth-death layers, W_T as a sum over the eigenpairs of the symmetrized killed generator, with nonnegative weights | `simulations/code/exact.py` | `bd_window` (`eigh_tridiagonal` of the symmetric tridiagonal matrix, weights `(V.T @ s) ** 2`) | |
| Numerical method | "Above 200 states, SciPy's expm_multiply ... replaces the eigendecomposition" | `simulations/code/exact.py` | `_SPECTRAL_MAX = 200` in `bd_window` | |
| Numerical method | "The non-birth-death chains of the extensions and the sweep chain of Remark 4.4 use an LU solve for stationary laws and a dense matrix exponential up to 400 states, with expm_multiply above" | `simulations/code/exact.py`, `simulations/code/exact_experiments.py` | the chains of `LinearCTMC` (`batch_name_chain`, `strategic_chain`, `providers_chain` and `exposure_chain`) and `addr_sweep_generator` go through `ctmc_stationary` (`np.linalg.solve` up to `_DENSE_MAX = 400` states, sparse `spsolve` above) and `ctmc_window` (`expm` up to 400 up-states, `expm_multiply` above). The birth-death chains of the extensions, the per-name pool (`name_window_perunit`) and the theta = infinity limit of exposure (`_exposure_window_fn` in `exact_experiments.py`), use `bd_window` | |
| Numerical method | "Frontiers are Brent roots (tolerance 10^-10)" | `simulations/code/exact.py` | `beta_star(..., xtol=1e-10)` | |
| Numerical method | each root is the frontier "by a single-crossing grid check for the other chains" | `R4_strategic_censor.json`, `R5_diversification.json`, `R10_perunit_normalization.json`, output of `extra_values.py` | `single_crossing` (true) in R4 `policies` (16 roots), R5 (18) and R10 (4). `extra_values.py` lines "single-crossing grid check" for the burst roots (b = 2, 4, 8), the strike-all roots with a reserve (r = 1, 2, 4) and the strike-all time-average roots at k_max = 8 (0.313) and 32 (0.665, the root among the MDP points of Appendix C), all True. The theta = infinity frontiers of R8 are birth-death pools | EXTRA, file |
| Accuracy | "On 40 random birth-death chains the symmetric form agrees with a dense matrix exponential to 2 x 10^-14" | output of `exact.py` | line "spectral vs dense expm (40 random chains): max \|diff\| = 1.99e-14" | EXACT |
| Accuracy | "on constant-rate name pools with buffers of 300 to 1,200 it agrees with expm_multiply to 4.4 x 10^-15" | output of `exact.py` | line "spectral vs Krylov (m = 300..1200): max \|diff\| = 4.44e-15" | EXACT |
| Accuracy | the independent implementation "reproduces the 120 interval frontiers ... to 2.5 x 10^-11" | not in the repository (Appendix E) | the 120 frontiers are the rows of `R2_frontiers.json` `table` (alpha in {0.9, 0.95, 0.99}, T in {1, 2, 5, 10, 20}, k_max in {2, ..., 256}) | |
| Implementation check | "Across the ten simulation experiments (about 2,800 values)" | `R1_exact_validation.json` | `n_points` of the comparisons of E1 to E10 (E1 40, E2 148 + 148, E3 500 + 500, E5 21, E6 1029, E7 100, E8 100, E9 100, E10 28 + 28 + 6 + 6) plus `E4.n_cells` (65), 2,819 in all | file |
| Implementation check | they "agree within Monte Carlo error where standard errors exist and to within 0.009 elsewhere" | `R1_exact_validation.json` | as in Section 5.2 (0.0086 at most outside the interval values of E2) | SIM |
| Implementation check | "In a 148-point sweep of interval availability at T = 5 against beta (k_max in {4, 8, 16, 32}, 24 seeds)" | `R1_exact_validation.json`, `E2_phase_transition.json` | `E2.stats_interval.n_points` (148 = 4 x 37 betas) and `E2.seeds` (24). E2 `kmaxes` | SIM |
| Implementation check | "the largest difference is 0.0052" | `R1_exact_validation.json` | `E2.stats_interval.max_abs_diff` (0.00520) | SIM |
| Implementation check | "99.3% of the differences lie within three standard errors" | `R1_exact_validation.json` | `E2.stats_interval.frac_within_3se` (0.9932) | SIM |

## Appendix C Extension Models

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "Each extension changes one ingredient of the model, keeps the canonical address layer, and is a finite chain solved exactly" | `simulations/code/exact.py`, `simulations/code/exact_experiments.py` | the chains `batch_name_chain`, `strategic_chain`, `providers_chain` and `exposure_chain` and the per-name pool `name_rates_perunit`, each multiplied by the canonical address window `addr_window(8, 1, 3, T)` in R1 (E7), R4, R5, R8 and R10 | |
| opening | Monte Carlo simulations checked the chains for strategic timing, providers, exposure and the sweeps "(16 seeds per configuration, all \|z\| < 2.4)" | `R4_strategic_censor.json`, `R5_diversification.json`, `R8_mint_exposure.json`, `R7_sync_discovery.json` | `mc_check[].mc_seeds` (16). The largest \|z\| over `z_window`, `z_timeavg` and `z` is 2.26 (R4), 1.72 (R5), 2.32 (R8) and 1.10 (R7) | SIM |
| Bursts and providers | "With P = 1 the model is the burst model with b = k_max at nominal burn ratio k_max beta" | `R5_diversification.json`, `R1_exact_validation.json` | 8 x `R5 by_kmax["8"].P["1"].pooled.beta_star_interval` (0.066099) equals `R1 E7.per_b["8"].beta_star_exact_root` (0.066099) | file |
| Strategic block timing | relative value iteration "finds strike-all optimal at all 17 points tested (beta from 0.05 to 2.0 at k_max = 8 and from 0.1 to 1.5 at k_max = 32, plus each buffer's time-average strike-all frontier)" | `R4_strategic_censor.json` | `best_response_timeavg_mdp.rows`: 9 betas and the root 0.313 at k_max = 8, 6 betas and the root 0.665 at k_max = 32 (`is_strike_all_root`), all with `optimal_policy_equals_strike_all` true | SIM |
| Mint-time exposure | "At nine tested points (k_max = 8, T = 5, rho in {0.25, 0.5, 0.9}, beta in {0.1, 0.3, 0.6}), the window probability differs from its limit as theta -> infinity by at most 1.5 x 10^-4 at theta = 10^3 and 1.5 x 10^-5 at theta = 10^4" | `R8_mint_exposure.json` | `theta_inf_limit_check[].max_abs_diff_window` (largest 1.45e-4 at theta = 1e3 and 1.45e-5 at theta = 1e4, each the maximum over the three betas) | SIM |
| after the proof of Proposition 5.5 | "At k_max = 8 the bound (1 - rho) beta* gives 0.496, 0.331, 0.165 and 0.066" | output of `extra_values.py` | line "Appendix C, bound (1 - rho) beta*" | EXTRA |
| after the proof of Proposition 5.5 | "slightly below the exact frontiers of Section 5.4" | `R8_mint_exposure.json` | `table["8"]["inf"]` (0.510, 0.352, 0.185, 0.078) | SIM |
| Per-name discovery | "A censor that finds each live name at its own rate delta burns at rate delta K, so the pool is the birth-death chain with death rate delta k in state k" | `simulations/code/exact.py` | `name_rates_perunit` and `name_window_perunit` | |
| Per-name discovery | "At k_max = 8 the target (0.95,5) holds up to delta = 0.212 per mint interval" | `R10_perunit_normalization.json`, output of `extra_values.py` | `results["8"]["delta=lam_disc"].delta_at_beta_star` (0.21223, `single_crossing` true). R10's other two normalizations reach the target at the same delta. `extra_values.py` recomputes it, line "the target (0.95, 5) holds up to delta" | SIM, EXTRA |
| Per-name discovery | "There the censor burns 0.952 names per mint interval while a name is live, the rate that step 7 of Section 7 estimates" | `R10_perunit_normalization.json`, output of `extra_values.py` | `results["8"]["delta=lam_disc"]`: `realized_burn_at_beta_star` (0.94293 names per mint interval, delta E[K]) / (1 - `pi0_at_beta_star` (0.00947)) = 0.952. `extra_values.py` line "there it burns" | SIM, EXTRA |
| Per-name discovery | "against beta* = 0.661 for a constant-rate censor" | `R10_perunit_normalization.json` | `results["8"]["constant_rate"].beta_star_interval` (0.66134) | SIM |
| Per-name discovery | "By flow balance that rate is Pr[K < k_max]/Pr[K >= 1], which rises with delta, because a larger delta never leaves more live names (Lemma A.2)" | output of `extra_values.py`, `R10_perunit_normalization.json` | line "by flow balance": Pr[K < k_max] / Pr[K >= 1] = 0.943 / 0.991 = 0.952, computed from the stationary law without counting burns. Pr[K < k_max] equals the burns per mint interval, `realized_burn_at_beta_star` in R10 (0.94293). Line "that rate rises with delta": a grid check of the rise for delta up to beta* (True). Beyond beta* the rate, delta E[K \| K >= 1], exceeds delta and so beta* | EXTRA, SIM |
| Per-name discovery | "Keeping that estimate below beta* is thus conservative against this censor too" | output of `extra_values.py` | line "that rate rises with delta": the rate equals beta* = 0.661 at delta = 0.0999, where A_5 = 0.997, above the target 0.95. An estimate below beta* thus means delta < 0.0999, well inside the delta = 0.212 up to which the target holds | EXTRA |

## Appendix D Data Sources and Processing

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| opening | "four analyses of public data, covering burn units, Snowflake, literature parameters and minting economics" | `data/burn_units/`, `data/snowflake/`, `data/literature/`, `data/minting/` | `data/README.md` | |
| opening | "None made a new measurement or used an account, key or approval, and all requests were paced" | `data/burn_units/fetchlib.py`, `data/snowflake/fetch_raw.py`, `data/literature/fetch_sources.py`, `data/minting/fetch.py` | at least 2 s between requests to one host (`MIN_GAP`), 1.5 s (`PACE_S`), 3 s (`PACE_S`) and 2 s (`PACE_S`, 20 s for crt.sh). No credentials. The Tor GitLab request of the burn-units analysis sends only the cookie that the site's own 403 page sets. In the minting manifest, `method` is POST only for the keyless Porkbun pricing API | |
| opening | "No human subjects are involved. The Tor and Snowflake statistics are published aggregates, and the pipelines identify issue threads by URL and date, comments by position and time, and commits by hash, never by author, and do not redistribute them" | `data/snowflake/SOURCES.md`, `data/literature/derived/params_table.csv`, `data/burn_units/derived/qualitative_events.csv`, `data/snowflake/analysis.py` | sources S1 and S2 of `SOURCES.md`, CollecTor's broker statistics and Tor Metrics' user estimates, are aggregates. The burn-units table cites each issue thread by `url` and `date`. GitHub comments are located by position and UTC time (`page` = `comment N (...)`, also in `quote_verification.csv`). The Snowflake analysis keeps rdsys-admin commits as the first 10 hex digits of the hash and the commit date (`commit`, `commit_date_utc`). Some downloaded inputs name people, for example the issue threads (their commenters' user names), the four Snowflake commit patches (their authors' names and e-mail addresses) and Tor's release notes (the contributors they credit, a few with e-mail addresses), and no raw input ships | file |
| opening | "a fetch script downloaded the raw files on 2026-10-03 and recorded the URL, retrieval time, SHA-256 hash, size and license of each in a manifest" | `data/burn_units/raw/manifest.json`, `data/snowflake/raw/manifest.json`, `data/literature/raw/manifest.json`, `data/minting/raw/manifest.json` | 64, 202, 24 and 202 entries, all retrieved on 2026-10-03 (UTC), with `url`, `retrieved_utc`, `sha256`, `size_bytes` and `license` | SNOW-MANIFEST, LIT-MANIFEST |
| opening | "an analysis script rebuilds the derived data offline" | `data/burn_units/analysis.py`, `data/snowflake/analysis.py`, `data/literature/analysis.py`, `data/minting/analysis.py` | each reads only `raw/` and makes no network access | |
| opening | "An independent rerun reproduced the derived tables byte for byte" | `data/burn_units/derived/README.md`, `data/snowflake/derived/README.md`, `data/literature/derived/README.md`, `data/minting/derived/README.md` | the SHA-256 of every shipped file, checked after a rerun on the paper's inputs. Only `generated_utc` in `data/burn_units/derived/run_meta.json` differs | |
| opening | "and an independent reimplementation, which is not part of the artifact, recomputed each number these analyses report" | not in the repository | | |
| Registry data | "Russia's blocking registry, read through the zapret-info mirror, lists the names, URLs and addresses under blocking orders, some of them for illegal content" | `data/burn_units/SOURCES.md`, `data/burn_units/fetch.py` | source 5 (Roskomnadzor registry, legal blocking orders), whose dumps have the fields `IP;domain;URL;org;decision;date`, as `zi_extract()` also notes | file |
| Registry data | "Each registry file was streamed through a filter that kept only the hostnames that lie under one of 19 platform suffixes, with their decision dates. No URL path was kept" | `data/burn_units/fetch.py` | `zi_extract()`, `step_zi()`, `step_zi_history()` and `step_antifilter()`. The registry extracts have the columns `platform`, `field`, `value` and `decision_date`. The antifilter extract keeps only the matching host names of `domains.lst`, one per line, without dates | |
| Registry data | "The full files were hashed for provenance and then deleted" | `data/burn_units/raw/manifest.json` | `upstream_files` or `upstream_sha256`, `upstream_lines` and `upstream_header` | file |
| Registry data | "No listed name, URL or address was resolved or fetched" | `data/burn_units/fetch.py`, `data/burn_units/analysis.py` | only dataset hosts are contacted, and `analysis.py` makes no network access | |
| Registry data | "the paper and the artifact report registry content only as aggregates, namely counts and dates per platform" | `data/burn_units/derived/ru_registry_platform_summary.csv`, `data/burn_units/derived/ru_registry_timeseries.csv`, `data/burn_units/derived/ru_antifilter_platform_summary.csv`, `data/burn_units/derived/ru_ooni_vs_registry.csv` | counts and dates per platform. The extracts and `ooni_platform_domains.csv` do not ship | BURN |
| Licenses | "OONI-derived data are licensed CC BY-NC-SA 4.0" | `LICENSE` | part 3 lists the 8 OONI-derived files, all in `data/burn_units/derived/` | |
| Licenses | "Sources without a license are cited and not redistributed" | `data/*/raw/README.md`, `data/snowflake/raw/manifest.json` | each `raw/` ships only `README.md` and `manifest.json`. The Snowflake manifest marks 91 files with `redistribute` false. `porkbun_tld_prices.csv`, `ct_log_list_summary.csv` and `doc_text/` of the minting analysis do not ship | SNOW-MANIFEST |
| Licenses | "The artifact ships scripts, manifests and derived data" | `data/README.md`, `data/*/derived/README.md` | 16, 12, 6 and 12 derived files for burn units, Snowflake, literature and minting, with their SHA-256 | |
| Licenses | "Live sources such as the registrar's price list can give different numbers on a new download, but the shipped derived data keep the paper's numbers" | `data/minting/derived/porkbun_summary.csv`, `data/minting/raw/README.md` | metrics `cheapest_first_year_usd` and `n_tlds_first_year_lt_2usd`. Section 4 of `raw/README.md` lists the live sources | MINT |
| Burn units | "GFWatch ..., which lists only the names that China blocked by DNS, from 2020-03-20 to 2024-09-06" | `data/burn_units/derived/cn_gfwatch_platform_summary.csv`, `data/burn_units/analysis.py` | the smallest `gfw_first_any` and the largest `gfw_lc_max`. `GFW_START` and `GFW_END` | BURN |
| Burn units | "OONI aggregates cover China from July to September 2026 (`azurefd.net` from August 2025) and Iran and Russia from October 2024 to September 2026" | `data/burn_units/derived/ooni_platform_summary.csv`, `data/burn_units/derived/run_meta.json`, `data/burn_units/fetch.py` | `ooni_window`: CN 2026-07-01 to 2026-10-01, IR and RU 2024-10-01 to 2026-10-01 (end exclusive). `azurefd_episode.first_measured_day` (2025-08-02). `OONI_QUERIES` | BURN |
| Burn units | "IRBlock lists names found blocked by scans from outside Iran between November 2024 and 15 January 2025" | `data/burn_units/derived/burn_units.csv`, `data/burn_units/SOURCES.md` | Iran rows, `evidence`. Source 4 | file |
| Burn units | "The registry data are seven snapshots from 2021-12-31 to 2025-10-01" | `data/burn_units/derived/ru_registry_timeseries.csv`, `data/burn_units/raw/manifest.json` | `snapshot`. `upstream_header` | BURN |
| Burn units | "A tenant name is a registrable domain under a platform suffix, or an Azure Front Door endpoint name" | `data/burn_units/analysis.py` | `tenant_of()` | |
| Burn units | "In OONI, a hostname with at least three non-failed measurements counts as tested, and as blocked if at least half are anomalous or confirmed" | `data/burn_units/derived/run_meta.json`, `data/burn_units/derived/burn_units.csv` | `thresholds`, `OONI_MIN_MEAS` (3) and `OONI_BLOCK_SHARE` (0.5). `coverage_source` | BURN |
| Burn units | "First dates of tenant blocks in GFWatch are upper bounds on their onset, while suffix rules are dated by daily tests of the bare suffix, so tenant-to-suffix gaps are lower bounds" | `data/burn_units/derived/burn_units.csv`, `data/burn_units/derived/cn_gfwatch_platform_summary.csv`, `data/burn_units/SOURCES.md` | `first_date_meaning` of the China rows, an upper bound on onset, and for `workers.dev`, `vercel.app` and `herokuapp.com` "suffix_date = bare suffix first seen DNS-blocked". `gfw_suffix_onset_source` of the four platforms with a suffix rule, "first_checked of the bare suffix (zone-file SLD, tested daily)". Source 1, `first_checked`, an upper bound for tenant names and tight for a bare suffix | file |
| Burn units | "A missing suffix rule shows absence of evidence, not absence of blocking" | `data/burn_units/derived/burn_units.csv` | `notes` of the ? cells | file |
| Snowflake | "Section 6.2 uses CollecTor's Snowflake broker statistics, Tor Metrics' bridge-user estimates and event timeline" | `data/snowflake/SOURCES.md`, `data/snowflake/raw/manifest.json` | sources S1 to S3 | |
| Snowflake | "48 versions of Tor's Connection Assist settings" | `data/snowflake/derived/summary.json` | `rdsys.n_commits` (48, from 2022-02-25 10:50:45 to 2026-03-18 11:23:50), `rdsys.first_commit` and `rdsys.last_commit` | SNOW |
| Snowflake | "Internet Outage Detection and Analysis (IODA) events (from 2022-01-26) to exclude shutdown days" | `data/snowflake/derived/summary.json` | `ioda.n_events` (848), `ioda.first_event` (2022-01-26 22:40:00) and `ioda.excluded_days_primary` (ru 8, ir 305, cn 82, tm 162) | SNOW, SNOW-SUMMARY |
| Snowflake | "For the Turkmenistan block and the end of Fastly's fronting, both open-ended, each change compares the initial week with the median over the 14 valid days before" | `data/snowflake/derived/event_table.csv`, `data/snowflake/analysis.py` | rows `TM-front-2021-10` / `tm` and `Fastly-2024-03-01` / `ALL`: `primary_estimator` (`pre14`), `window_kind` (`point (+7 d)`) and `pre_valid_days` (14). The constants `PRE_DAYS`, `PRE_LOOKBACK` and `POINT_DURING` | SNOW |
| Snowflake | "User counts measure usage, not availability, and polls are not users" | | an interpretation | |
| Snowflake | "Derived tables omit the client credentials in those settings" | `data/snowflake/analysis.py` | `parse_bridge_line()` keeps methods and host names only. No shipped file contains a credential | |
| Parameters and minting | "a table of 110 values from 18 papers and one field report" | `data/literature/derived/params_table.csv` | 110 rows from 19 distinct `raw_file` values, 18 PDF papers and one HTML page (net4people/bbs issue 111) | LIT |
| Parameters and minting | "each with a verbatim quote found at its cited location" | `data/literature/derived/params_table.csv`, `data/literature/derived/quote_verification.csv` | `verified` True in all 110 rows (`match` strict 108, strict_nohyphen 2). 137 of 137 quotes found, counting the 27 supporting quotes | LIT |
| Parameters and minting | "No source measures lambda_burn" | `data/literature/derived/params_table.csv`, `data/literature/derived/name_layer_mapping.csv` | no row gives a burn rate for names a defender mints. The closest rows (G26, G27, G29, G30 and G46) concern address units exposed in public channels, and `name_layer_mapping.csv` marks its scenarios built from G26 and G27 as `measured (address units, not names)` in column `basis` | LIT, file |
| Parameters and minting | "one registrar's price list on one day" | `data/minting/derived/porkbun_summary.csv` | metric `retrieved_utc` (2026-10-03T21:46:19Z) | MINT |
| Parameters and minting | "three free certificate authorities" | `data/minting/derived/doc_facts.csv` | facts `le_free` (Let's Encrypt), `gts_free` (Google Trust Services) and `zerossl_unlimited` (ZeroSSL). `acme_mint_rates.csv` lists the rate limits of the three | MINT |
| Parameters and minting | "hosting platforms' documentation" | `data/minting/derived/platform_names.csv`, `data/minting/derived/doc_facts.csv` | column `facts` of the 12 platforms, for example `gh_one_site` (GitHub Pages), `cf_workers_per_account` (Cloudflare Workers), `vercel_projects` (Vercel), `netlify_instant` (Netlify) and `firebase_36_sites` (Firebase Hosting), each quoted from the platform's documentation at its `source_url` | file |
| Parameters and minting | "`crt.sh` lookups of platform wildcard certificates" | `data/minting/derived/crtsh_platform_wildcards.csv` | rows with `identity_queried` `*.github.io` (2), `*.netlify.app` (2) and `*.web.app` (1). Column `cert_evidence` of `platform_names.csv` records that the lookups of `*.pages.dev` and `*.vercel.app` failed | MINT |
| Parameters and minting | "ICANN's zone-file access terms" | `data/minting/derived/doc_facts.csv` | facts `zfa_daily`, `zfa_active_names`, `zfa_agreement`, `zfa_deny`, `ra_once_per_24h` and `ra_icann_daily` | MINT |
| Parameters and minting | "a CT honeypot study" | `data/minting/derived/scheitle2018_table4.csv` | Table 4 of Scheitle et al., with facts `scheitle_dns_73s_3min` and `scheitle_11_names` | MINT |
| Parameters and minting | "the CT protocol, policies and log list" | `data/minting/derived/doc_facts.csv`, `data/minting/derived/summary.json` | facts `rfc6962_mmd`, `rfc6962_precert`, `chrome_ct_required`, `chrome_two_scts`, `chrome_embed_scts`, `chrome_mmd_caps`, `chrome_incorporate_mmd` and `apple_ct_required`. Key `ct_log_list.log_list_version` (93.3) | MINT |
| Parameters and minting | "No source shows whether any censor watches CT logs or zone files" | | no source of this analysis observes censor behavior | |

## Appendix E Simulator, Solver and Reproducibility

| Paragraph | Statement | File | Key, column or row | Command |
|---|---|---|---|---|
| Event-driven simulator | sample paths by the next-event method, each layer simulated on its own, the system down on the union of their down intervals | `simulations/code/rotation_game.py` | `simulate_address`, `simulate_domain` and `combine` | |
| Event-driven simulator | "The first 10% of each run is discarded as warm-up" | `simulations/code/rotation_game.py`, `simulations/code/run_experiments.py` | `GameParams.warmup_frac = 0.1`. `warmup = 0.1 * horizon` in E6, E9 and E10 | |
| Event-driven simulator | interval availability "is computed exactly, without discretization, as one minus the share of window starts" in the union of (s_j - T, e_j) | `simulations/code/rotation_game.py` | `interval_up_probability` | |
| Event-driven simulator | "Runs last 1.2 x 10^4 to 4 x 10^4 mint intervals" | `simulations/code/run_experiments.py` | `horizon` (12,000 in E1 to 40,000 in E6) | |
| Event-driven simulator | "each point averages 12 to 24 independent seeds" | `simulations/code/run_experiments.py` | `seeds = 24`. E3 averages `max(8, seeds // 2)` = 12, although `E3_mu_heatmap.json` records the run setting, 24, in `_meta.seeds` | |
| Runtimes | "The ten simulation experiments take about one hour on one core" | `E1_ip_geometric.json` to `E10_discovery_robustness.json` | `_meta.runtime_s` (sum 3,356 s). Two reruns took 57 and 58 minutes | file |
| Runtimes | the exact suite "takes 302 seconds of wall time on a 20-core workstation (Python 3.13.7, NumPy 2.2.4, SciPy 1.15.3)" | `R1_exact_validation.json` to `R13_rotation_speed.json` | `_meta.runtime_s` (sum 300.7 s), `_meta.python`, `_meta.numpy` and `_meta.scipy` | file |
| Runtimes | "Short computations outside the suite, in extra_values.py, give values and checks that no result file stores, such as the address windows at lambda_a T = 15 and 60, the wall-clock thresholds of Section 5.3, the bound after Corollary B.2 and the per-name burn rate of Appendix C" | `simulations/code/extra_values.py` | its output (see Sections 5.2, 5.3 and 7 and Appendices B and C above). Besides the values named, it prints the values at beta = 2 of Figure 2's description, the exact thresholds behind the 7% of Section 5.3, the time of one frontier in step 3 of Section 7 and the single-crossing checks of Appendix B. For Appendix C it also prints the bound (1 - rho) beta*, the flow-balance form of the per-name rate, a grid check that this rate rises with delta and the delta at which the rate equals beta*. The accuracy figures of Appendix B come from `exact.py` (EXACT) | EXTRA |
| Runtimes | "The independent implementation of Appendix B is a separate check outside the artifact" | not in the repository | | |
| Reproducibility | `python3 exact.py` "runs a self-test of the solver", `python3 exact_experiments.py` "reruns the exact experiments" and `python3 run_experiments.py` "reruns the event-driven simulations" | `simulations/code/` | `simulations/results/README.md` describes the reruns and how to compare them with the shipped files | EXACT |
| Reproducibility | `python3 paper/figures/make_figures.py` "redraws Figures 1 and 2 from these result files and checks the plotted series against the exact solver" | `paper/figures/make_figures.py` | reads `E2_phase_transition.json`, `R1_exact_validation.json` and `R2_frontiers.json`, 85 checks | FIG |
| Reproducibility | "Exact result files record their runtime, a timestamp, the library versions and the SHA-256 hashes of exact.py and exact_experiments.py" | the 13 R files | `_meta.runtime_s`, `_meta.generated_utc`, `_meta.python`, `_meta.numpy`, `_meta.scipy` and `_meta.code_sha256` | file |
| Reproducibility | "the simulation seeds are fixed in run_experiments.py" | `simulations/code/run_experiments.py` | the seed expression of each experiment, for example `10_000 + s` for the address layer of E2 | |
| Reproducibility | "Independent reruns of the exact suite reproduced all 12,248 numbers in its 13 result files to within 3 x 10^-14, the residue of a random norm estimate in SciPy's expm_multiply" | the 13 R files | 12,248 are the numeric values other than booleans and `_meta.runtime_s` (13,171 with booleans). The comparison in `simulations/results/README.md` prints 12,238 of them and the 10 file sizes of R1's `inputs` separately. Reruns on the reference workstation reproduced every number exactly except up to five window values of R9, which the paper does not report and which differed by at most 2.2e-14. They come from chains of 625 states, which `ctmc_window` solves with `expm_multiply`, whose norm estimate draws from NumPy's global random generator, which the code does not seed | |
| Reproducibility | "Rerunning the figure script with the same library builds (those above, with Ubuntu's Matplotlib 3.10.1 package, fontTools 4.55.3 and pandas 3.0.6) reproduces both figures byte for byte" | `figures/frontier.pdf`, `figures/phase.pdf` | SHA-256 `ecbec4445a888dd50611c6743d6be0108d22cb042ce270bab0d316df1c762526` and `e70893b49affd7c4bfefa1ac073f397456a50f8c46bc29ca51b9dd53cb2d6b6d`. `cmp` after `make_figures.py --outdir` (Matplotlib build 3.10.1+dfsg1-4, fontTools 4.55.3) | FIG |
| Reproducibility | "Appendix D describes the data pipelines" | `data/` | see Appendix D above and `data/README.md` | |
| Reproducibility | "One command regenerates every figure, and the code, data pipelines and results are openly available" | `paper/figures/make_figures.py`, the repository | `make_figures.py` writes `figures/frontier.pdf` and `figures/phase.pdf`. `README.md` describes the contents and what is not included, namely the independent implementation of Appendix B and the independent reimplementation of Appendix D | FIG |
