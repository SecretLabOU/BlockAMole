# Snowflake outputs (`data/snowflake/derived/`)

This directory ships with this README and the 12 files marked "yes" under
"All outputs". `data/snowflake/analysis.py` writes every file listed there
from `data/snowflake/raw/` without network access.
`data/snowflake/raw/README.md` explains how to download the inputs, which the
artifact does not ship.

## Rebuild

From the repository root, run

```
cd data/snowflake
python3 analysis.py --no-fig
```

- This writes the 20 tables and `summary.json` in under a minute.
- `python3 analysis.py` also draws a supplementary figure that the paper does
  not use. The figure step imports `simulations/code/figstyle.py` and
  `simulations/code/paper.mplstyle` from this repository. `summary.json` is
  written before the figure, so a failed figure step leaves every table and
  `summary.json` in place.
- `python3 analysis.py --out DIR` writes the outputs to `DIR` and leaves the
  shipped files untouched.
- The analysis needs Python 3 with NumPy and pandas, Matplotlib for the
  figure, and Poppler's `pdftotext` and `pdfinfo` for the quote checks in
  `churn_published.csv`. Tested with Python 3.13.7, NumPy 2.2.4, pandas
  3.0.6, Matplotlib 3.10.1 and Poppler 25.03.0.

On the paper's raw files, which the shipped `raw/manifest.json` lists
(`manifest.paper.json` after a download), a rerun writes all 12 shipped files
byte for byte. A new download differs in places (see
`data/snowflake/raw/README.md`), and the rebuilt files then differ too.

## Check the shipped files

This prints `OK` for each of the 12 shipped files, both as downloaded and
after a rerun on the paper's raw files. Run it from `data/snowflake/`. On
macOS, use `shasum -a 256 -c` instead of `sha256sum -c`.

```
sha256sum -c <<'EOF'
4efded3cfc7180645eb726f8555741092269724c21056ab9d5f70b6a7512037c  derived/churn_published.csv
11e6967ce9187e27f0b759e870baebf337f77bad6c64fa82f51a8fe39a31fdf9  derived/event_broker_metrics.csv
60d234726fe6de1c8e935a3e7fd430019ba6e7477809049e119a4d2f9df2e866  derived/event_table.csv
df31095b547d435381119830ec5a7d5af3aab64d564f38614d7afcd9883e1979  derived/event_table_sensitivity.csv
1c156ad13c8a8aa8e05020eb720b4b9289e17f110d995564e3bebe35f13311ac  derived/event_transport_comparison.csv
f9a02e74ac6c675ccfa11b474c1fcc5495db2e6d5ee1335d0c245bf44d67e444  derived/sf_broker_windows.csv
3971e680b11ff8c10df8ccf58a5f811047412d3ed77da6a6ea75086675167511  derived/sf_proxy_ips_summary.csv
f8e06e2ed9905472080caa93fd19e1ac8e67ace996f2c1c404c634c6452e8d36  derived/sf_rendezvous_country_method_daily.csv
edd7a51d677cd674bf49251de98232b638cedb97ccc33f08ec4ec3be81bbded4  derived/sf_rendezvous_monthly_country_method.csv
3383a2b387d9fa14008185014bcca82b232ab6b35f4e638d704d698e8e2fc3e3  derived/sf_rendezvous_recent_by_country_method.csv
102d41725473550308c3f4d5184cc313eb18900b6200d4177208e15930c90bd3  derived/summary.json
a88c21b4623bd002e5f8b074f9881aec9c0b0be97e06b7812bc8fd70c3f1d0cb  derived/tormetrics_frac_validity.csv
EOF
```

## The paper's numbers

This prints every Snowflake number in the paper from the shipped files. Run it
from `data/snowflake/`.

```
python3 - derived <<'EOF'
import datetime as dt, json, sys
from pathlib import Path
import pandas as pd
D = Path(sys.argv[1])
S = json.loads((D / "summary.json").read_text())
p = pd.read_csv(D / "sf_proxy_ips_summary.csv").set_index("period").loc["v2_post_gap"]
e = pd.read_csv(D / "event_table.csv")
b = pd.read_csv(D / "event_broker_metrics.csv")
c = pd.read_csv(D / "churn_published.csv").set_index("claim")
m = pd.read_csv(D / "sf_rendezvous_recent_by_country_method.csv")
ev = lambda i, cc: e[(e.event_id == i) & (e.country == cc)].iloc[0]
brk = lambda k: b[(b.event_id == "Fastly-2024-03-01") & (b.country == "ALL") & (b.metric == k)].chg_pct.iloc[0]
q = lambda k: "PDF page %d, found %s" % (c.loc[k, "pdf_page"], c.loc[k, "verified_in_pdf_text"])
tm, fa = ev("TM-front-2021-10", "tm"), ev("Fastly-2024-03-01", "ALL")
rn, rd, fr = S["rdsys_rendezvous_names"], S["rdsys"], S["fastly_http_recovery"]
r50 = dt.date.fromisoformat(fr["first_date_ge50pct"])
print("Sec. 6.2 proxy addresses per day:", p.ips_total_median, "(median of", p.n_windows, "windows,", p.date_from, "to", p.date_to + ")")
print("Sec. 6.2 half the 2023 pool turns over in about", c.loc["half_pool_turnover_about_20h", "value"], "hours,", q("half_pool_turnover_about_20h"))
print("Sec. 6.2 rendezvous methods the broker counts:", ", ".join(sorted(m.method.unique())))
print("Sec. 6.2 Turkmenistan from", tm.start + ": users", tm.pre_low, "->", tm.during_low, "| 'not until August 2022',", q("tm_alt_front_confirmed_aug2022"))
print("Sec. 6.2 Fastly from", fa.start + ": HTTP polls %.1f%%, users %.1f%%, proxy addresses %.1f%%" % (brk("http_polls"), fa.chg_primary_low_pct, brk("ips_total")))
print("Sec. 6.2 HTTP polls back to half of", fr["pre_median_2024_02_16_to_29"], "on", r50, "=", (r50 - dt.date(2024, 3, 1)).days, "days after 2024-03-01")
print("Sec. 6.2 rendezvous names introduced", rn["n_distinct"], "and retired", rn["n_distinct"] - rn["n_present_at_last_commit"], "| first added by year", dict(sorted(rn["first_added_by_year"].items())))
print("App. D settings versions", rd["n_commits"], "(" + rd["first_commit"], "to", rd["last_commit"] + ") | first IODA event", S["ioda"]["first_event"])
print("App. D baseline", tm.primary_estimator, "/", fa.primary_estimator + ",", tm.pre_valid_days, "/", fa.pre_valid_days, "valid days before, window", tm.window_kind)
print("Sec. 3 DTLS supported_groups quote,", q("ru_2021_dtls_supported_groups"))
EOF
```

On the shipped files it prints the following.

```
Sec. 6.2 proxy addresses per day: 148718.5 (median of 6 windows, 2026-09-28 to 2026-10-03)
Sec. 6.2 half the 2023 pool turns over in about 20.0 hours, PDF page 12, found True
Sec. 6.2 rendezvous methods the broker counts: amp, http, sqs
Sec. 6.2 Turkmenistan from 2021-10-24: users 28.0 -> 2.0 | 'not until August 2022', PDF page 16, found True
Sec. 6.2 Fastly from 2024-03-01: HTTP polls -85.8%, users -32.5%, proxy addresses -2.1%
Sec. 6.2 HTTP polls back to half of 1482920.0 on 2024-04-06 = 36 days after 2024-03-01
Sec. 6.2 rendezvous names introduced 19 and retired 11 | first added by year {'2022': 2, '2023': 3, '2024': 9, '2025': 2, '2026': 3}
App. D settings versions 48 (2022-02-25 10:50:45 to 2026-03-18 11:23:50) | first IODA event 2022-01-26 22:40:00
App. D baseline pre14 / pre14, 14 / 14 valid days before, window point (+7 d)
Sec. 3 DTLS supported_groups quote, PDF page 14, found True
```

Notes on these values.

- User numbers are Tor Metrics estimates, the low bound of the estimate for
  Turkmenistan and the single estimate of the worldwide series, whose low and
  high changes are therefore equal. `pre_low` is the median over the 14 valid
  days before the event and `during_low` the median over the valid days of
  its first week.
- The broker changes in `event_broker_metrics.csv` compare the median of the
  first 7 broker windows (2024-03-01 to 2024-03-07) with the median of the 14
  windows before (2024-02-16 to 2024-02-29).
- HTTP rendezvous polls are the broker's `client-http-count`, the polls that
  use the HTTP rendezvous method, domain-fronted or not.
- The 36 days run from 2024-03-01 to the first window dated on or after
  2024-03-02 whose HTTP polls reach half of the 2024-02-16 to 2024-02-29
  median.
- "Tor configured other fronts the same day" rests on the author time of
  rdsys-admin commit `4d979dbb1e`, 2024-03-01 20:57:26 UTC, in
  `data/snowflake/raw/gitlab/rdsys-admin/circumvention_log.tsv` after the
  download. The derived tables use commit times, so `summary.json` dates
  this commit 2024-03-02 00:43:46 (`rdsys_rendezvous_names.removal_bursts`).
- The 19 names are the configured Snowflake fronts, AMP-cache fronts and SQS
  hosts (`rdsys_name_spans_all_countries.csv`, kinds `front`, `amp_front`
  and `sqs_host`). 8 of them are still configured in the last version, so 11
  were retired.

## All outputs

The files are in `data/snowflake/derived/`. Every file is written by
`python3 analysis.py`, run from `data/snowflake/`. `--no-fig` skips the three
figure files. The section is the part of `main()` in `analysis.py` that writes
the file.

| File | Ships | Section | Content | Paper statement it supports |
|---|---|---|---|---|
| `sf_broker_windows.csv` | yes | (i) broker windows | one row per CollecTor broker window (2,598): proxy addresses by type, NAT and country, polls by method, matches, timeouts, counting definition and quality flag | basis of every broker number in Section 6.2 |
| `sf_proxy_ips_summary.csv` | yes | (i) | proxy-address medians and quartiles by period and year | Section 6.2, 148,719 proxy addresses per day |
| `sf_rendezvous_country_method_daily.csv` | yes | (ii) rendezvous | polls per window by country and method, with a validity flag | basis of the method statement in Section 6.2 |
| `sf_rendezvous_recent_by_country_method.csv` | yes | (ii) | polls and shares by country and method for three recent periods | Section 6.2, every method the broker counts (HTTP, AMP cache, SQS) |
| `sf_rendezvous_monthly_country_method.csv` | yes | (ii) | monthly polls by country and method | context, not reported |
| `shutdown_day_masks.csv` | no, daily IODA scores | masks | per country and day, IODA coverage hours and scores, timeline shutdown hours, exclusion flags | the shutdown screen behind `event_table.csv` |
| `tormetrics_frac_validity.csv` | yes | masks | Tor Metrics `frac` per day, its centred 15-day median and the 15-point rule | the coverage screen behind `event_table.csv` |
| `ioda_long_events_not_used_in_primary_mask.csv` | no, copies IODA records | masks | the 14 IODA events longer than 14 days | context, not reported |
| `timeline_snowflake_related.csv` | no, verbatim timeline rows that name hosts other than Tor's fronts | timeline extract | the Snowflake, fronting and shutdown rows of the Tor Metrics timeline | the source rows of the event dates in `analysis.py`, among them Fastly on 1 March 2024 |
| `event_table.csv` | yes | (iii) events | 31 event and country rows with every baseline, placebo percentile and exclusion count | Introduction and Section 6.2 (Fastly users -32.5%, Turkmenistan 28 to 2), Appendix D (baselines) |
| `event_table_sensitivity.csv` | yes | (iii) | the per-country rows under three other shutdown rules (no screen, any IODA overlap, two or more IODA sources), computed without excluding the days of other events | context, not reported |
| `event_transport_comparison.csv` | yes | (iii) | the per-country windows for obfs4, webtunnel, meek and plain bridges (`<OR>`) | context, not reported |
| `event_broker_metrics.csv` | yes | (iii) | broker polls, matches, timeouts and proxy addresses around each event | Section 6.2 (-85.8% and -2.1%), Introduction (proxy addresses barely changed) |
| `rdsys_circumvention_snowflake_config.csv` | no, rdsys-admin content | rdsys-admin | per settings version and country, the Snowflake methods, fronts, AMP front, SQS host and STUN hosts, without credentials | Section 6.2 (the names each method uses), Appendix D (no credentials) |
| `rdsys_name_events.csv` | no, rdsys-admin content | rdsys-admin | names added and removed between versions | Section 6.2 (other fronts configured after Fastly's change) |
| `rdsys_name_lifetimes.csv` | no, rdsys-admin content | rdsys-admin | configured spells per country and name | context, not reported |
| `rdsys_name_spans_all_countries.csv` | no, rdsys-admin content | rdsys-admin | per name, first addition and last removal | Section 6.2 (19 introduced, 11 retired) |
| `rdsys_removal_bursts.csv` | no, rdsys-admin content | rdsys-admin | names retired per commit and the failure its subject states | context, not reported |
| `rdsys_commit_user_changes.csv` | no, rdsys-admin content | rdsys-admin | user changes around configuration commits | context, not reported |
| `churn_published.csv` | yes | (iv) publications | published churn figures and case statements, each quote searched in the PDF text, with its page | Introduction (a front domain for the rendezvous), Section 6.2 (about 20 hours, the names the rendezvous methods use, the Turkmenistan block lasting months), Section 3 (the DTLS block) |
| `summary.json` | yes | all | the headline values in machine-readable form | Introduction (a front domain for the rendezvous), Section 6.2 (the configured rendezvous methods, the Fastly fronts failing together, 36 days, 19 and 11), Appendix D (48 versions, IODA from 2022-01-26) |
| `fig_snowflake.pdf`, `fig_snowflake_preview.png`, `fig_snowflake_data.json` | no, not in the paper | figure | event-time indices of users and polls for four events | none |

## Licenses

The shipped tables are computed from CollecTor and Tor Metrics data and the
Tor Metrics timeline, which are CC0. The event tables use IODA only to screen
days and report only counts of excluded days. `summary.json` also holds counts
derived from IODA and rdsys-admin, the time of IODA's first event and 14 short
commit subjects from rdsys-admin, quoted as citations. `churn_published.csv` and the `description` column of
`event_table.csv` quote short passages of Bocovich et al. (2024), Chen et al.
(2026), the Tor Metrics timeline and a net4people/bbs issue title. No shipped
file contains an IODA record or daily score, an rdsys-admin configuration, a
client credential or a raw file.
