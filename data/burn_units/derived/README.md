# Outputs of the burn-units analysis

`python3 analysis.py`, run in `data/burn_units`, writes the files in this directory from
`../raw/`. It makes no network access and takes about 1.5 to 2 minutes and 0.6 GB of
memory. The artifact ships 16 of the 20 files it writes, the ones that hold aggregates
only, computed from the paper's raw files. The paper's numbers can be read from them
without downloading anything, as "Values in the paper" below shows.

A rerun needs

- the complete `../raw/` directory, including `../raw/manifest.json`, as
  `../raw/README.md` describes,
- `git`, numpy, pandas and matplotlib,
- `simulations/code/figstyle.py` and `simulations/code/paper.mplstyle` from the top of
  the artifact, for the last step, the timeline figure. `analysis.py` writes every table
  before that step, so a failure there leaves the tables complete but ends the run with
  an error.

`analysis.py` overwrites the files in this directory. To keep the shipped ones, copy them
first with `cp -r derived derived.paper` in `data/burn_units`. During the run it unpacks
the gfwlist history into a temporary `.tmp_gfwlist_*` directory in `data/burn_units` and
deletes it at the end. A complete run prints this last line.

```
done: 57 cells; {'CN': {'tenant': 10, 'mixed': 4, 'insuff': 4, 'suffix': 1}, 'IR': {'insuff': 12, 'tenant': 4, 'suffix': 3}, 'RU': {'tenant': 14, 'none': 4, 'mixed': 1}}
```

A line `[gfwatch] missing` means a China cell rests on incomplete data, and
`[qual] quote not found` means a qualitative page has changed.

## Files

Every file is written by `python3 analysis.py`. The function named is the one in
`analysis.py` that computes it.

| file | in the artifact | function | content | used in the paper |
|---|---|---|---|---|
| `burn_units.csv` | yes | `classify()` | 57 rows, one per censor and platform suffix, with granularity, first, suffix and lifted dates, OONI tested and blocked host names, evidence and notes | Table 1, Section 6.1, Introduction |
| `burn_units_table.tex` | yes | `write_tex()` | LaTeX rendering of the matrix with its own caption, label and legend | no, the paper typesets Table 1 itself (see below) |
| `burn_units_evidence_long.csv` | yes | `evidence_long()` | every per-source metric behind each cell, in long form | traceability of Table 1 |
| `cn_gfwatch_platform_summary.csv` | yes | `gfwatch_summary()` | China, GFWatch per platform: blocked names, tenants, inferred rules, suffix-rule onset, first tenant, tenants before the rule, class | Table 1 China column, Section 6.1, Appendix D |
| `cn_gfwlist_platform_history.csv` | yes | `gfwlist_history()` | gfwlist suffix-rule dates and tenant rule lines per platform | no |
| `ir_irblock_platform_summary.csv` | yes | `irblock_summary()` | Iran, IRBlock per platform: bare suffix blocked by DNS or HTTP, blocked names and tenants, machine-generated names | Table 1 Iran column, Section 6.1 |
| `ooni_cn_azurefd_daily.csv` | yes | `azurefd_episode()` | China, daily OONI counts summed over the 39 Azure Front Door endpoints, 2025-08-02 to 2026-09-30 | Table 1 △, Appendix D |
| `ooni_cn_monthly.csv` | yes | `ooni_monthly_cn()` | China, tested, blocked and clear host names per month and platform | Table 1 △ |
| `ooni_platform_summary.csv` | yes | `ooni_summary()` | OONI per censor and platform: window, host names seen, tested, blocked, clear and mixed, tenants tested, bare-suffix measurements | Table 1 legend, Section 6.1, Appendix D |
| `qualitative_events.csv` | yes | `qualitative_events()` | three dated reports with short quotes checked against the raw pages | Section 3, Scope (Tor GitLab issue 40064) |
| `ru_antifilter_platform_summary.csv` | yes | `antifilter_summary()` | Russia, antifilter list of 2026-10-02 per platform: entries, tenants, suffix entry | the Russian ∅ cells |
| `ru_ooni_vs_registry.csv` | yes | `ru_ooni_vs_registry()` | OONI Russia measurements of names that are or are not registry-listed, per platform | Section 6.1, Table 1 caption and ‡ |
| `ru_registry_platform_summary.csv` | yes | `registry_summary()` | Russia, registry dump of 2025-10-01 per platform: host entries, masks, URL hosts, tenants, suffix entry, decision dates, first snapshots | Table 1 Russia column and ‡ |
| `ru_registry_timeseries.csv` | yes | `registry_summary()` | Russia, entries and tenants per platform in each of the 7 dumps | Section 6.1, Appendix D |
| `run_meta.json` | yes | `main()` | run time, gfwlist head, IRBlock line totals, Azure Front Door episode, OONI file statistics, Heroku routing names, low-coverage registry names, thresholds, class counts | Table 1 △ and ∗, Section 6.1, Appendix D |
| `tranco_bare_suffix_ranks.csv` | yes | `tranco_bare()` | Tranco rank of each bare suffix on 4 dates | no, it shows that each bare suffix was in the daily test input of GFWatch and IRBlock |
| `ooni_platform_domains.csv` | no | `main()`, from `ooni_domain_table()` | OONI counts and class per host name | no |
| `cn_gfwlist_platform_line_events.csv` | no | `gfwlist_history()` | gfwlist rule lines that mention a platform suffix, with the dates they were added and deleted | no |
| `ooni_raw_mechanism_checks.csv` | no | `ooni_raw_mechanisms()` | DNS, TCP and TLS outcomes of the 5 raw OONI measurements | no |
| `fig_burn_units_timeline.pdf` | no | `make_figure()` | escalation timelines | no |

The four files that the artifact leaves out are not used by the paper.
`ooni_platform_domains.csv` lists the 6,614 host names under the 19 suffixes that OONI
measured, 4,764 of which count as tested, and 123 of the 6,614 also appear in a registry
extract or in antifilter's list. `cn_gfwlist_platform_line_events.csv` and
`ooni_raw_mechanism_checks.csv` name 32 and 3 individual hosts. The figure is not in the
paper. A rerun writes all four. Do not publish them.

## SHA-256 of the shipped files

| file | SHA-256 |
|---|---|
| `burn_units.csv` | `a2c1566f93a5dfc1b4a51deb528d403a8d137efaa7353476d564b5255d85388b` |
| `burn_units_evidence_long.csv` | `46e9c5850e484a7ae401471988af5ef7bb7a5e1cbfac6b188d3999d207735791` |
| `burn_units_table.tex` | `6cc8b6aa9c763e946c18e0f3ba42e8eaa8fd26c923e5da12be015bdad1b4a012` |
| `cn_gfwatch_platform_summary.csv` | `7645d1d289ade191b62136ed0293f764cd6e12e9367c6d08a0d49e49085aea10` |
| `cn_gfwlist_platform_history.csv` | `1fe963acd1b0a49a65f3b4d3bbd7455f8d22ea7a1bae95fa01f06dd91e0d8531` |
| `ir_irblock_platform_summary.csv` | `3ff68a15cf3b0415446e0909ead6e12ee1f64180bf4aa5bf3516cfedee5b5185` |
| `ooni_cn_azurefd_daily.csv` | `2210584bc3fdefdf8e540744e005000298e553d905e2c6f6288ac090fca76bf9` |
| `ooni_cn_monthly.csv` | `547079c98e9105783b275b6ef6fe1020bcfb8d7e78a7df6b0d7ffc6ba6d2e263` |
| `ooni_platform_summary.csv` | `b4b7c0bdd3249b963abf314c22b5644f4c955fe78cc3b8dd874c0d9b7dff2dfa` |
| `qualitative_events.csv` | `6d978be8c904997c70a6bc8ea660455ee21b8886b7b16ca4375cff83f0c49828` |
| `ru_antifilter_platform_summary.csv` | `6521d3877e0751747cb7d3e8097d6a919f1e039149c2da2079c0878f14c3574d` |
| `ru_ooni_vs_registry.csv` | `a041a6d83d9becc59ffb263f5f06b4e74209e0209033d5dcc1841de6725824bf` |
| `ru_registry_platform_summary.csv` | `c3316cff00de2653d8dddc774492dbe98781085b052233a4a83c2e36811ed4b6` |
| `ru_registry_timeseries.csv` | `cf6a2a17ac42b3f930d1a3e761b8fef11f5241ffd675013dcf4a9d208e593852` |
| `run_meta.json` | `ddab86c09c3e7bad40a03581ae12fbefa67de47d3ad36e6bfdab61ab9079cb14` |
| `tranco_bare_suffix_ranks.csv` | `2b689760c101d96f4a382617b16c5a55ffa9fda5ce899f3070d9fdb8257530cf` |

To check them, run this in `data/burn_units`. On macOS use `shasum -a 256 -c` in place
of `sha256sum -c`.

```sh
sha256sum -c <<'EOF'
a2c1566f93a5dfc1b4a51deb528d403a8d137efaa7353476d564b5255d85388b  derived/burn_units.csv
46e9c5850e484a7ae401471988af5ef7bb7a5e1cbfac6b188d3999d207735791  derived/burn_units_evidence_long.csv
6cc8b6aa9c763e946c18e0f3ba42e8eaa8fd26c923e5da12be015bdad1b4a012  derived/burn_units_table.tex
7645d1d289ade191b62136ed0293f764cd6e12e9367c6d08a0d49e49085aea10  derived/cn_gfwatch_platform_summary.csv
1fe963acd1b0a49a65f3b4d3bbd7455f8d22ea7a1bae95fa01f06dd91e0d8531  derived/cn_gfwlist_platform_history.csv
3ff68a15cf3b0415446e0909ead6e12ee1f64180bf4aa5bf3516cfedee5b5185  derived/ir_irblock_platform_summary.csv
2210584bc3fdefdf8e540744e005000298e553d905e2c6f6288ac090fca76bf9  derived/ooni_cn_azurefd_daily.csv
547079c98e9105783b275b6ef6fe1020bcfb8d7e78a7df6b0d7ffc6ba6d2e263  derived/ooni_cn_monthly.csv
b4b7c0bdd3249b963abf314c22b5644f4c955fe78cc3b8dd874c0d9b7dff2dfa  derived/ooni_platform_summary.csv
6d978be8c904997c70a6bc8ea660455ee21b8886b7b16ca4375cff83f0c49828  derived/qualitative_events.csv
6521d3877e0751747cb7d3e8097d6a919f1e039149c2da2079c0878f14c3574d  derived/ru_antifilter_platform_summary.csv
a041a6d83d9becc59ffb263f5f06b4e74209e0209033d5dcc1841de6725824bf  derived/ru_ooni_vs_registry.csv
c3316cff00de2653d8dddc774492dbe98781085b052233a4a83c2e36811ed4b6  derived/ru_registry_platform_summary.csv
cf6a2a17ac42b3f930d1a3e761b8fef11f5241ffd675013dcf4a9d208e593852  derived/ru_registry_timeseries.csv
ddab86c09c3e7bad40a03581ae12fbefa67de47d3ad36e6bfdab61ab9079cb14  derived/run_meta.json
2b689760c101d96f4a382617b16c5a55ffa9fda5ce899f3070d9fdb8257530cf  derived/tranco_bare_suffix_ranks.csv
EOF
```

With the paper's raw files and Python 3.13.7, numpy 2.2.4, pandas 3.0.6, Matplotlib
3.10.1 and git 2.51.0, a rerun reproduces every shipped file byte for byte except
`run_meta.json`, whose `generated_utc` records the time of the run. After a new download,
the files built from live sources differ, above all OONI, as `../raw/README.md`
explains. Compare their values with the ones below.

## Table 1 and `burn_units_table.tex`

The paper typesets Table 1 itself and does not input `burn_units_table.tex`. Both follow
`burn_units.csv`, and their 57 cells agree except one.

- **China, `azurefd.net`.** `classify()` treats the OONI day-level episode as a
  platform-wide block, so `burn_units.csv` labels the cell
  `mixed (tenant, then suffix)`, with `suffix_date` 2025-08-02 and `lifted_date`
  2026-09-05, and `burn_units_table.tex` prints ○→● '25 with a dagger. The paper prints
  ○ △. The ○ is the GFWatch class, `tenant` in `cn_gfwatch_platform_summary.csv`, from
  2 tenants blocked by name in 2024. The △ marks the temporary impairment recorded under
  `azurefd_episode` in `run_meta.json`. The paper does not count the episode as a
  suffix-wide rule, because all tested endpoints lie in one Azure Front Door zone (a02),
  and whether the name alone or the address and name together triggered it is
  undetermined. `class_counts` in `run_meta.json` follows `burn_units.csv`, so for China
  it counts `tenant` 10 and `mixed` 4 where the paper shows 11 ○ and 3 ○→●.
- **Typesetting.** The generated table prints `--` where the paper prints ∅ and sets the
  years in `\scriptsize`. Its caption, label (`tab:burn-units`, the paper's is
  `tab:burn`), legend and column spacing are its own.
- **Legend.** The paper's legend names the seven China cells that rest on GFWatch alone,
  defines ‡ as a wildcard entry whose enforcement OONI does not confirm, and reads ∗ as
  "the bare suffix and Heroku's routing names are largely not blocked". The generated
  legend instead gives the source windows and explains the dagger with the episode's
  dates.

## Reading Table 1 from `burn_units.csv`

- The `granularity` column gives the symbol. `suffix-wide rule` is ●,
  `mixed (tenant, then suffix)` is ○→●, `per-name (tenant)` is ○,
  `insufficient coverage` is ? and `none observed` is ∅.
- A year after ● or ○→● is the year of `suffix_date`. For China it is the first day
  GFWatch saw the bare suffix blocked, and for Russia the first dump with the suffix
  entry. Iran has no years, because IRBlock gives no onsets, and its dates are the end of
  the IRBlock window, 2025-01-15. ≤'20 marks `appspot.com`, whose rule is present on
  GFWatch's first day, 2020-03-20 (`gfw_onset_left_censored` in
  `cn_gfwatch_platform_summary.csv`).
- ‡ marks the Russian cell with a suffix entry (`pages.dev`), and ∗ marks China's
  `herokuapp.com`. The `notes` column gives the numbers behind both.
- `n_tested` and `n_blocked` count OONI host names, as `coverage_source` states. A host
  name counts as tested with at least 3 non-failed measurements and as blocked when at
  least half of them are anomalous or confirmed. In China and Iran, a platform without
  any blocked name in GFWatch or IRBlock would be ∅ only if OONI tested at least 5 of its
  names and found none blocked, and is ? otherwise. No cell meets that bar, so all such
  cells are ?. These thresholds are in `run_meta.json` under `thresholds`.

## Values in the paper

Run this in `data/burn_units`. It reads only the shipped files.

```sh
python3 - <<'EOF'
import csv, datetime, json

def rows(name):
    with open("derived/" + name, newline="") as f:
        return list(csv.DictReader(f))

cells = rows("burn_units.csv")
gfw = {r["platform"]: r for r in rows("cn_gfwatch_platform_summary.csv")}
ooni = {(r["censor"], r["platform"]): r for r in rows("ooni_platform_summary.csv")}
irb = {r["platform"]: r for r in rows("ir_irblock_platform_summary.csv")}
ts = {(r["platform"], r["snapshot"]): r for r in rows("ru_registry_timeseries.csv")}
reg = {r["platform"]: r for r in rows("ru_registry_platform_summary.csv")}
month = {(r["month"], r["platform"]): r for r in rows("ooni_cn_monthly.csv")}
meta = json.load(open("derived/run_meta.json"))
ep, her, low = meta["azurefd_episode"], meta["cn_heroku_routing"], meta["ru_registry_listed_low_coverage"]

SYM = {"suffix-wide rule": "●", "mixed (tenant, then suffix)": "○→●", "per-name (tenant)": "○",
       "insufficient coverage": "?", "none observed": "∅"}

def symbol(r):
    cc, g, d = r["censor"], r["granularity"], r["suffix_date"]
    if cc == "CN" and r["platform"] == "azurefd.net":   # the paper prints the GFWatch class plus △
        return SYM["per-name (tenant)"] + " △" if gfw["azurefd.net"]["gfw_class"] == "tenant" else "check"
    s = SYM[g]
    if g in ("suffix-wide rule", "mixed (tenant, then suffix)") and cc != "IR":
        s += " ≤'20" if cc == "CN" and d <= "2020-03-20" else " '" + d[2:4]
    if cc == "RU" and g in ("suffix-wide rule", "mixed (tenant, then suffix)"):
        s += " ‡"
    if cc == "CN" and r["platform"] == "herokuapp.com":
        s += " ∗"
    return s

table = {}
for r in cells:
    table.setdefault(r["platform"], {})[r["censor"]] = symbol(r)
order = ["github.io", "pages.dev", "workers.dev", "r2.dev", "trycloudflare.com", "vercel.app", "netlify.app",
         "herokuapp.com", "onrender.com", "fly.dev", "deno.dev", "appspot.com", "web.app", "firebaseapp.com",
         "run.app", "cloudfront.net", "lambda-url.<region>.on.aws", "azurewebsites.net", "azurefd.net"]
print("Table 1 (China, Iran, Russia)")
for p in order:
    print(f"  {p:27s} {table[p]['CN']:12s} {table[p]['IR']:12s} {table[p]['RU']}")

def tested(cc, p):
    o = ooni[(cc, p)]
    return f"{int(o['ooni_blocked']):,} of {int(o['ooni_tested']):,}"

few = ["pages.dev", "netlify.app", "onrender.com", "fly.dev", "deno.dev", "firebaseapp.com", "azurewebsites.net"]
print("Table 1 legend")
print("  China, OONI tested names in 2026 (fewer than five):",
      ", ".join(f"{p} {ooni[('CN', p)]['ooni_tested']}" for p in few))
print("  appspot.com rule first seen", gfw["appspot.com"]["gfw_suffix_onset"],
      "at the start of GFWatch:", gfw["appspot.com"]["gfw_onset_left_censored"])
print(f"  △ {ep['endpoints']} Azure Front Door endpoints from {ep['first_measured_day']} to "
      f"{ep['last_day_with_anomaly_before_lift']}: {ep['share_before_lift']:.1%} of "
      f"{ep['measurements_before_lift']:,} measurements anomalous, then {ep['share_after_lift']:.1%} of "
      f"{ep['measurements_after_lift']} from {ep['lift_day']}")
print("    azurefd.net names blocked per month:",
      ", ".join(f"{m} {month[(m, 'azurefd.net')]['blocked']} of {month[(m, 'azurefd.net')]['tested']}"
                for m in ("2026-07", "2026-08", "2026-09")))
pg, rp = reg["pages.dev"], ooni[("RU", "pages.dev")]
print(f"  ‡ *.pages.dev (decision date {pg['reg_suffix_decision_date']}) absent from the dump of "
      f"{pg['reg_last_snapshot_without_suffix']}, present in that of {pg['reg_first_snapshot_suffix']}; "
      f"OONI RU names under it {rp['ooni_names_any']}, tested {rp['ooni_tested']}; bare pages.dev "
      f"{round(float(rp['ooni_bare_share']) * int(rp['ooni_bare_meas']))} of {rp['ooni_bare_meas']} anomalous")
hb = ooni[("CN", "herokuapp.com")]
print(f"  ∗ bare herokuapp.com {round(float(hb['ooni_bare_share']) * int(hb['ooni_bare_meas']))} of "
      f"{hb['ooni_bare_meas']} anomalous; routing names {her['ooni_clear']} of {her['ooni_tested']} clear "
      f"({her['ooni_mixed']} intermittent); other names {her['others_blocked']} of {her['others_tested']} blocked")
print("  ∅ registry tenants:", ", ".join(f"{p} {reg[p]['reg_tenants']}"
                                        for p in ("r2.dev", "trycloudflare.com", "fly.dev", "on.aws")))
print("Section 6.1")
g = gfw["github.io"]
print(f"  GFWatch github.io tenants {g['gfw_tenants']}, suffix rule {g['gfw_suffix_rule']}; "
      f"OONI China github.io {tested('CN', 'github.io')} blocked")
print(f"  IRBlock github.io tenants {irb['github.io']['irb_any_tenants']}, bare suffix blocked "
      f"{irb['github.io']['irb_bare_blocked']}")
print(f"  registry cloudfront.net tenants {int(ts[('cloudfront.net', '2021-12-31')]['tenants']):,} (2021-12-31), "
      f"{int(ts[('cloudfront.net', '2025-10-01')]['tenants']):,} (2025-10-01)")
for p in ("workers.dev", "vercel.app", "herokuapp.com"):
    r = gfw[p]
    y0, m0, d0 = map(int, r["gfw_tenant_first"].split("-"))
    y1, m1, d1 = map(int, r["gfw_suffix_onset"].split("-"))
    gap = (datetime.date(y1, m1, d1) - datetime.date(y0, m0, d0)).days
    print(f"  {p}: first tenant {r['gfw_tenant_first']}, suffix rule {r['gfw_suffix_onset']}, "
          f"{gap} days; OONI China 2026 {tested('CN', p)} blocked")
print(f"  Russia, registry-listed names with at most 2 valid OONI measurements: {low['names']} names on "
      f"{len(low['platforms'])} platforms, {low['valid']} measurements, {low['anomalous']} anomalous")
print("Appendix D")
dates = [r["gfw_first_any"] for r in gfw.values() if r["gfw_first_any"]]
ends = [r["gfw_lc_max"] for r in gfw.values() if r["gfw_lc_max"]]
print("  GFWatch rows from", min(dates), "to", max(ends))
print("  OONI windows (until exclusive):",
      ", ".join(f"{cc} {ooni[(cc, 'github.io')]['ooni_window']}" for cc in ("CN", "IR", "RU")),
      "; azurefd.net from", ep["first_measured_day"])
snaps = sorted({s for _, s in ts})
print(f"  registry snapshots {len(snaps)}, {snaps[0]} to {snaps[-1]}")
t = meta["thresholds"]
print(f"  tested: >= {t['OONI_MIN_MEAS']} non-failed measurements; blocked: >= {t['OONI_BLOCK_SHARE']:.0%} "
      f"anomalous or confirmed; too few: fewer than {t['MIN_TESTED']} tested names")
EOF
```

It prints the following.

```
Table 1 (China, Iran, Russia)
  github.io                   ○            ○            ○
  pages.dev                   ○            ●            ○→● '24 ‡
  workers.dev                 ○→● '22      ?            ○
  r2.dev                      ?            ?            ∅
  trycloudflare.com           ?            ●            ∅
  vercel.app                  ○→● '22      ?            ○
  netlify.app                 ○            ○            ○
  herokuapp.com               ○→● '22 ∗    ●            ○
  onrender.com                ○            ?            ○
  fly.dev                     ○            ?            ∅
  deno.dev                    ○            ?            ○
  appspot.com                 ● ≤'20       ?            ○
  web.app                     ○            ?            ○
  firebaseapp.com             ○            ?            ○
  run.app                     ?            ?            ○
  cloudfront.net              ○            ○            ○
  lambda-url.<region>.on.aws  ?            ?            ∅
  azurewebsites.net           ○            ○            ○
  azurefd.net                 ○ △          ?            ○
Table 1 legend
  China, OONI tested names in 2026 (fewer than five): pages.dev 4, netlify.app 1, onrender.com 0, fly.dev 0, deno.dev 1, firebaseapp.com 0, azurewebsites.net 3
  appspot.com rule first seen 2020-03-20 at the start of GFWatch: True
  △ 39 Azure Front Door endpoints from 2025-08-02 to 2026-09-04: 64.6% of 2,551 measurements anomalous, then 0.4% of 240 from 2026-09-05
    azurefd.net names blocked per month: 2026-07 159 of 172, 2026-08 166 of 177, 2026-09 6 of 166
  ‡ *.pages.dev (decision date 2024-05-06) absent from the dump of 2024-05-06, present in that of 2024-05-09; OONI RU names under it 14, tested 0; bare pages.dev 0 of 90 anomalous
  ∗ bare herokuapp.com 2 of 17 anomalous; routing names 17 of 18 clear (1 intermittent); other names 357 of 358 blocked
  ∅ registry tenants: r2.dev 0, trycloudflare.com 0, fly.dev 0, on.aws 0
Section 6.1
  GFWatch github.io tenants 259, suffix rule False; OONI China github.io 6 of 980 blocked
  IRBlock github.io tenants 27, bare suffix blocked False
  registry cloudfront.net tenants 30 (2021-12-31), 10,224 (2025-10-01)
  workers.dev: first tenant 2021-03-21, suffix rule 2022-04-30, 405 days; OONI China 2026 984 of 1,100 blocked
  vercel.app: first tenant 2022-07-15, suffix rule 2022-08-26, 42 days; OONI China 2026 1,008 of 1,008 blocked
  herokuapp.com: first tenant 2020-08-31, suffix rule 2022-10-11, 771 days; OONI China 2026 357 of 376 blocked
  Russia, registry-listed names with at most 2 valid OONI measurements: 88 names on 9 platforms, 43 measurements, 0 anomalous
Appendix D
  GFWatch rows from 2020-03-20 to 2024-09-06
  OONI windows (until exclusive): CN 2026-07-01..2026-10-01, IR 2024-10-01..2026-10-01, RU 2024-10-01..2026-10-01 ; azurefd.net from 2025-08-02
  registry snapshots 7, 2021-12-31 to 2025-10-01
  tested: >= 3 non-failed measurements; blocked: >= 50% anomalous or confirmed; too few: fewer than 5 tested names
```

How these lines map to the paper:

- The Table 1 block reproduces all 57 cells of Table 1. The Introduction's examples
  come from it: China blocks `workers.dev` and Iran `pages.dev` suffix-wide, and both
  block `github.io` per name.
- The legend block gives the seven China cells with fewer than five OONI-tested names,
  the ≤'20 of `appspot.com`, and the numbers behind △, ‡, ∗ and ∅.
- The Section 6.1 block gives 259 GFWatch tenants of `github.io` and no suffix rule,
  6 of 980 tested names blocked, 27 IRBlock tenants, 30 and 10,224 `cloudfront.net`
  tenants in the registry, the gaps of 405, 42 and 771 days, the OONI counts 984 of
  1,100, 1,008 of 1,008 and 357 of 376, and the registry-listed names behind "OONI
  measures too few platform entries to confirm their enforcement".
- The Appendix D block gives the GFWatch window, the OONI windows (China July to
  September 2026, `azurefd.net` from August 2025, Iran and Russia October 2024 to
  September 2026), the seven registry snapshots and the OONI thresholds. The IRBlock
  window, November 2024 to 2025-01-15, is in the `evidence` column of the Iran rows of
  `burn_units.csv`.

## Licenses, sources and host names

- Files with OONI-derived numbers are licensed CC BY-NC-SA 4.0, following OONI's data
  license. These are `burn_units.csv`, `burn_units_table.tex`,
  `burn_units_evidence_long.csv`, `ooni_cn_azurefd_daily.csv`, `ooni_cn_monthly.csv`,
  `ooni_platform_summary.csv`, `ru_ooni_vs_registry.csv` and `run_meta.json`.
- The other files hold aggregates of the following sources, which a user of the files
  should cite: GFWatch (Hoang et al., USENIX Security 2021), gfwlist (LGPL-2.1), IRBlock
  (Tai et al., USENIX Security 2025, CC BY 4.0, doi:10.5281/zenodo.15572895),
  Roskomnadzor's registry through the zapret-info mirror, antifilter.download, Tranco
  (Le Pochat et al., NDSS 2019) and the qualitative reports named in
  `qualitative_events.csv`.
- Files built from Russia's registry and from antifilter's list hold counts and dates
  per platform only, with no registry names or URLs.
- No file in this directory names an individual tenant or host on the 19 platforms. The
  files name the platform suffixes, the zones of Heroku's routing names and of Azure
  Front Door (`ingress.herokuapp.com`, `a02.azurefd.net`), the pattern
  `<worker>.<account>.workers.dev` and one OONI measurement ID. `qualitative_events.csv`
  also holds the URLs of its three sources and, inside its short quotes, two public
  service names, Cloudflare's ECH name and the cover name used in the WebTunnel report.
- `../fetch.py`, `../raw/manifest.json` and the file table of `../SOURCES.md` name the
  42 hosts that the OONI steps query, because a new download needs them. These are the 39
  Azure Front Door endpoints of `OONI_AZUREFD_CN`, with their zone apex, and the two
  `workers.dev` names of the `ooni_raw` step. One endpoint label is also part of the
  name of an `ooni/list_*.json` file. All 42 come from OONI's public measurements, and
  none of them is in a registry extract or in antifilter's list.
